from tokenisation import Tokenizer
import shelve
import os
import re


class TokenWindow(object):
    def __init__(self, allString, pos, start, end):
        self.allString = allString  # all the line
        self.positions = pos  # list of Positions
        self.win_start = start  # start window
        self.win_end = end  # end window

    def __repr__(self):
        s = '{}, {}, {}, {}'.format(self.allString, str(self.positions), self.win_start, self.win_end)

        return s

    def __eq__(self, obj):
        '''
        check if two tokens are equal (it is so when they have the
        same first and last symbol
        '''
        return self.positions == obj.positions and self.win_start == obj.win_start and self.win_end == obj.win_end

    def window_is_junction(self, obj):
        return (self.win_start <= obj.win_end and
                self.win_end >= obj.win_start and
                obj.allString == self.allString)

    def get_BB_string(self):
        """
        Creates a string that represents context. Query words are 'highlighted'
        i.e. surrounded by HTML tags <b></b>.
        Returns:
            String cut to size of the context with query words highlighted.
        """
        result_string = self.allString[self.win_start:self.win_end]

        for position in reversed(self.positions):
            end = position.end - self.win_start
            start = position.start - self.win_start
            result_string = result_string[:end] + '</b>' + result_string[end:]
            result_string = result_string[:start] + '<b>' + result_string[start:]
        return result_string


class SearchEngine(object):
    """
    Class containing methods for working with database.
    """

    def __init__(self, database=''):
        """
        Create an instance of SearchEngine class.
        """
        if database != '':
            self.database = shelve.open(database)
        else:
            self.database = None

    def __del__(self):

        if self.database is not None:
            self.database.close()

    def search(self, query):
        """
        Search database and return files
        and positions for the searched word
        """
        if self.database is None:
            return {}

        if not isinstance(query, str):
            raise ValueError
        return self.database.get(query, {})

    def multiple_search(self, query):
        if not isinstance(query, str):
            raise ValueError
        if not query or self.database is None:
            return {}

        tokenizer = Tokenizer()
        """
        tokenisation of query, create list of tokens
        """
        searchlist = []
        for token in tokenizer.tokenize_generator_type(query):
            if token.t == 'A' or token.t == 'D':
                searchlist.append(token.s)       
        results_of_search = []   # search each token from query
        for token in searchlist:
            results_of_search.append(set(self.search(token)))        
        list_of_files = results_of_search[0]    # find files with all words from query
        for f in results_of_search:
            list_of_files = list_of_files & f       
        final_dict = {}  # create a dictionary of positions of all query tokens in files
        for f in list_of_files:
            final_dict[f] = []
            for token in searchlist:
                final_dict[f].extend(self.database[token][f])
            final_dict[f].sort()
        return final_dict

    def multiple_search_lim(self, query, offset, limit):    # with the limits for files

        if offset < 0:
            offset = 0

        if not isinstance(query, str):
            raise ValueError
        if not query or self.database is None:
            return {}

        tokenizer = Tokenizer()
        """
        tokenisation of query, create list of tokens
        """
        searchlist = []
        for token in tokenizer.tokenize_generator_type(query):
            if token.t == 'A' or token.t == 'D':
                searchlist.append(token.s)
        results_of_search = []   # search each token from query
        for token in searchlist:
            results_of_search.append(set(self.search(token)))
        list_of_files = results_of_search[0]     # find files with all words from query
        for f in results_of_search:
            list_of_files = list_of_files & f
        final_dict = {}  # create a dictionary of positions of all query tokens in files
        list_of_files = sorted(list_of_files)
        for i, f in enumerate(list_of_files):

            if i >= offset + limit:
                break
            if i < offset:
                continue

            final_dict[f] = []
            for token in searchlist:
                final_dict[f].extend(self.database[token][f])
            final_dict[f].sort()
        return final_dict

    def multiple_search_lim_gen(self, query, offset, limit):     # with the limits for files

        if offset < 0:
            offset = 0

        if not isinstance(query, str):
            raise ValueError
        if not query or self.database is None:
            return {}

        tokenizer = Tokenizer()
        """
        tokenisation of query, create list of tokens
        """
        searchlist = []
        for token in tokenizer.tokenize_generator_type(query):
            if token.t == 'A' or token.t == 'D':
                searchlist.append(token.s)
                
        results_of_search = []   # search each token from query
        for token in searchlist:
            results_of_search.append(set(self.search(token)))

        list_of_files = results_of_search[0]    # find files with all words from query
        for f in results_of_search:
            list_of_files = list_of_files & f

        final_dict = {}      # create a dictionary of positions of all query tokens in files
        list_of_files = sorted(list_of_files)
        for i, f in enumerate(list_of_files):

            if i >= offset + limit:
                break

            if i < offset:
                continue

            lists = []
            for token in searchlist:
                lists.append(self.database[token][f])

            final_dict[f] = self.merge_and_sort_lists(lists)

        return final_dict

    def merge_and_sort_lists(self, lists):
        iters = [iter(l) for l in lists if len(l) > 0]
        firsts = [next(it) for it in iters]

        while (len(firsts) != 0):
            m = min(firsts)
            yield m
            mpos = firsts.index(m)
            try:
                firsts[mpos] = next(iters[mpos])
            except StopIteration:
                iters.pop(mpos)
                firsts.pop(mpos)

    def find_window(self, findstr, window_len=3):
        """
        Search database and return files
        and positions for the searched word
        """

        if not isinstance(findstr, str):
            raise ValueError
        if not findstr:
            return {}

        windows = {}
        tokenizer = Tokenizer()
        result_dict = self.multiple_search(findstr)

        for file_key in result_dict:
            wins = []
            result_list = result_dict[file_key]

            for result_position in result_list:

                with open(file_key) as f:
                    for i, line in enumerate(f):
                        if i == result_position.string:
                            break
                line = line.strip("\n")

                right_context = line[result_position.start:]
                left_context = line[:result_position.end][::-1]

                for i, token in enumerate(tokenizer.generate_type_AD(left_context)):
                    if i == window_len:
                        break
                start = result_position.end - token.position - len(token.s)

                for i, token in enumerate(tokenizer.generate_type_AD(right_context)):
                    if i == window_len:
                        break
                end = result_position.start + token.position + len(token.s)

                win = TokenWindow(line, [result_position], start, end)  # create new window
                win = self.supplemented_window(win)  # expanding the window to the borders of the proposals
                wins.append(win)  # addind window to dictionary
                wins = self.join_windows({file_key: wins})[file_key]  # connection of Windows

            if len(wins) > 0:
                windows[file_key] = wins

        return windows

    def find_window_lim(self, findstr, window_len=3, offset=0, limit=0, winLimits=None):
        """
        Search database and return files
        and positions for the searched word
        witch limits and limits for file defined this function
        """

        if not isinstance(findstr, str):
            raise ValueError
        if not findstr:
            return {}

        windows = {}
        tokenizer = Tokenizer()
        result_dict = self.multiple_search(findstr)

        for f, file_key in enumerate(result_dict.keys()):
            wins = []
            if f >= offset + limit:
                break

            if f < offset:
                continue

            result_list = result_dict[file_key]

            if winLimits is not None:
                st = int(winLimits[f - offset][0])
                en = st + int(winLimits[f - offset][1])

                if len(result_list) < en:
                    en = len(result_list)

                result_list = result_list[st:en]

            for result_position in result_list:

                with open(file_key) as f:
                    for i, line in enumerate(f):
                        if i == result_position.string:
                            break
                line = line.strip("\n")

                right_context = line[result_position.start:]
                left_context = line[:result_position.end][::-1]

                for i, token in enumerate(tokenizer.generate_type_AD(left_context)):
                    if i == window_len:
                        break
                start = result_position.end - token.position - len(token.s)

                for i, token in enumerate(tokenizer.generate_type_AD(right_context)):
                    if i == window_len:
                        break
                end = result_position.start + token.position + len(token.s)

                win = TokenWindow(line, [result_position], start, end)  # create new window
                win = self.supplemented_window(win)  # expanding the window to the borders of the proposals
                wins.append(win)  # addind window to dictionary
                wins = self.join_windows({file_key: wins})[file_key]  # connection of Windows

            if len(wins) > 0:
                windows[file_key] = wins
            else:
                windows[file_key] = []

        return windows

    def find_window_lim_v2(self, findstr, window_len=3, offset=0, limit=0, winLimits=None):
        """
        Search database and return files
        and positions for the searched word
        witch limits and limits for file transfer in multiple_search 
        """

        if not isinstance(findstr, str):
            raise ValueError
        if not findstr:
            return {}

        windows = {}
        tokenizer = Tokenizer()

        # simply find 
        # result_dict = self.multiple_search_lim(findstr, offset, limit)

        # find with generators
        result_dict = self.multiple_search_lim_gen(findstr, offset, limit)

        for f, file_key in enumerate(result_dict.keys()):
            wins = []

            result_list = result_dict[file_key]

            st = 0
            en = 5

            if winLimits is not None:
                st = winLimits[f][0]  # offset for current tom
                en = st + winLimits[f][1]  # offset + limit for current tom

                if st < 0:
                    st = 0

            for result_position in result_list:

                with open(file_key) as f:
                    for i, line in enumerate(f):
                        if i == result_position.string:
                            break
                line = line.strip("\n")

                right_context = line[result_position.start:]
                left_context = line[:result_position.end][::-1]

                for i, token in enumerate(tokenizer.generate_type_AD(left_context)):
                    if i == window_len:
                        break
                start = result_position.end - token.position - len(token.s)

                for i, token in enumerate(tokenizer.generate_type_AD(right_context)):
                    if i == window_len:
                        break
                end = result_position.start + token.position + len(token.s)

                win = TokenWindow(line, [result_position], start, end)  # create new window
                win = self.supplemented_window(win)  # expanding the window to the borders of the proposals
                wins.append(win)  # addind window to dictionary
                wins = self.join_windows({file_key: wins})[file_key]  # connection of Windows

                
                if len(wins) == en:
                    break   # stop when the required number of Windows is found

            if len(wins) > 0:
                windows[file_key] = wins[st:]  # return the Windows from the required position (offset)
            else:
                windows[file_key] = []

        return windows

    def join_windows(self, in_dict):

        window_dict = {}

        for f, wins in in_dict.items():
            pr_win = None
            for win in wins:
                if pr_win is not None and pr_win.window_is_junction(win):
                    for pos in win.positions:
                        if pos not in pr_win.positions:
                            pr_win.positions.append(pos)
                            """
                            he looks at whether the pr_win variable is defined,
                            if yes, then checks whether the windows intersect,
                            if yes then intersects. otherwise, it looks again
                            whether the pr_win variable is defined; if so, it
                            adds it to the window array. pr_win equates to the
                            current window
                            """

                    pr_win.win_start = min(pr_win.win_start, win.win_start)
                    pr_win.win_end = max(pr_win.win_end, win.win_end)
                else:
                    if pr_win is not None:
                        window_dict.setdefault(f, []).append(pr_win)
                    pr_win = win
            if pr_win is not None:
                window_dict.setdefault(f, []).append(pr_win)
            else:
                window_dict.setdefault(f, [])

        return window_dict

    def supplemented_window(self, win):

        re_right = re.compile(r'[.!?] [A-ZА-Я]')
        re_left = re.compile(r'[A-ZА-Я] [.!?]')

        r = win.allString[win.win_end:]
        l = win.allString[:win.win_start + 1][::-1]
        if l:
            try:
                win.win_start = win.win_start - re_left.search(l).start()
            except:
                win.win_start = 0
        if r:
            try:
                win.win_end += re_right.search(r).start() + 1
            except:
                win.win_end = len(win.allString)
        return win

    def find_supplemented_window(self, findstr, window_len):
        """
        Searcher window without limits
        """
        window_dict = self.find_window(findstr, window_len)
        return window_dict

    def find_supplemented_window_lim_v2(self, findstr, window_len, offset=0, limit=0, winLimits=None):
        """
        Searcher window with limits. Key limits are processed in
        the method multiple_search_lim or multiple_search_lim_gen
        """
        window_dict = self.find_window_lim_v2(findstr, window_len, offset, limit, winLimits)
        return window_dict

    def find_supplemented_window_lim(self, findstr, window_len, offset=0, limit=0, winLimits=None):
        """
        Searcher window with limits. Key limits are processed in this method
        """
        window_dict = self.find_window_lim(findstr, window_len, offset, limit, winLimits)
        return window_dict

    def find_supplemented_window_lim_v3(self, findstr, window_len, offset=0, limit=0, winLimits=None):
        """
        Searcher window with limits. Working with
        generators in all methods except the last one
        """
        window_dict = self.find_window_lim_v3(findstr, window_len, offset, limit, winLimits)
        return window_dict


    def find_window_lim_v3(self, findstr, window_len=3, offset=0, limit=0, winLimits=None):
        """
        Search database and return files
        and positions for the searched word
        witch limits and limits for file transfer in multiple_search
        """
        if not isinstance(findstr, str):
            raise ValueError
        if not findstr:
            return {}

        # find with generators
        result_dict = self.multiple_search_lim_gen(findstr, offset, limit)

        windows = {}
        for f, file_key in enumerate(result_dict.keys()):
            """
            Create window for window_len. Return generator
            with window to the borders of the proposals 
            """
            context_wins_gen = self.context_window_generator(file_key, result_dict[file_key], window_len)
            """
            Return generator with connection of Windows.
            """
            join_wins_gen = self.join_windows_gen(context_wins_gen)

            st = 0
            en = 5
            if winLimits is not None:
                st = winLimits[f][0]  # offset for current tom
                en = st + winLimits[f][1]  # offset + limit for current tom

            if st < 0:
                st = 0

            wins = []
            for r in join_wins_gen:
                wins.append(r)  # addind window to dictionary
                if len(wins) == en:
                    break   # stop when the required number of Windows is found

            if len(wins) > 0:
                windows[file_key] = wins[st:]  # return the Windows from the required position (offset)
            else:
                windows[file_key] = []
        return windows


    
    def context_window_generator(self, file_name, contexts, window_len=3):
        """
        Generator context window with window_len  
        """
        tokenizer = Tokenizer()
        for result_position in contexts:
            """
            Find line for position
            """
            with open(file_name) as f:
                for i, line in enumerate(f):
                    if i == result_position.string:
                        break
            line = line.strip("\n")

            right_context = line[result_position.start:]
            left_context = line[:result_position.end][::-1]
            """
            Expanding the boundaries of the window according to the specified parameter
            Calculating of the beginning
            """
            for i, token in enumerate(tokenizer.generate_type_AD(left_context)):
                if i == window_len:
                    break
            start = result_position.end - token.position - len(token.s)
            """
            Expanding the boundaries of the window according to the specified parameter
            Calculating the end
            """
            for i, token in enumerate(tokenizer.generate_type_AD(right_context)):
                if i == window_len:
                    break
            end = result_position.start + token.position + len(token.s)

            win = TokenWindow(line, [result_position], start, end)  # create new window
            win = self.supplemented_window(win)  # expande the window to the borders of the proposals

            yield win

    def join_windows_gen(self, in_dict):
        """
        Generator join window  
        """
        pr_win = None
        for win in in_dict:
            if pr_win is not None and pr_win.window_is_junction(win):
                for pos in win.positions:
                    if pos not in pr_win.positions:
                        pr_win.positions.append(pos)
                        """
                        he looks at whether the pr_win variable is defined,
                        if yes, then checks whether the windows intersect,
                        if yes then intersects. otherwise, it looks again
                        whether the pr_win variable is defined; if so, it
                        adds it to the window array. pr_win equates to the
                        current window
                        """

                pr_win.win_start = min(pr_win.win_start, win.win_start)
                pr_win.win_end = max(pr_win.win_end, win.win_end)
            else:
                if pr_win is not None:
                    yield pr_win

                pr_win = win

        if pr_win is not None:
            yield pr_win
