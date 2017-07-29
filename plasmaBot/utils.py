import sys
import subprocess
import traceback
import colorama


class databaseTable(object):
    """A class meant to make Database Table generation less difficult."""
    def __init__(self, columns, datatypes, seed=[]):
        if len(columns) != len(datatypes):
            raise Exception('Invalid Table Suggested')

        self.columns = columns
        self.datatypes = datatypes
        self.seed = seed


class Printer:
    """Custom Printer Class used to communicate with terminal output."""

    def __init__(self, client=None):
        """Initiation for the printer class"""

        colorama.init()
        self.client = client
        self.Fore = colorama.Fore
        self.Back = colorama.Back
        self.Style = colorama.Style
        self.colorama = colorama
        self.tags = {0: '',
                     1: colorama.Back.MAGENTA + colorama.Fore.WHITE + '[PB5]' + colorama.Style.RESET_ALL + ' ',
                     2: '      ',
                     3: colorama.Back.RED + colorama.Fore.WHITE + 'ERROR' + colorama.Style.RESET_ALL + '\033[F: '}

    def ref_client(self, client):
        """Reference the Client object to the current Printer object"""
        self.client = client

    def clear_screen(self):
        """Clear the terminal screen of all text."""
        sys.stdout.write(colorama.ansi.clear_screen())

    def __print(self, content, *, tag=1, cmd=True, replace=True, beg_newline=False, end_newline=False, flush=True, color=''):
        """Default Print Method, Extended by other Methods"""

        replace = True if cmd else replace
        beg_newline = False if replace else beg_newline
        end_newline = True if cmd else end_newline
        flush = True if replace else flush

        content = self.tags[tag] + colorama.Style.RESET_ALL + str(color) + str(content) + colorama.Style.RESET_ALL

        if beg_newline: content = '\n' + content

        if replace: content = '\r' + content

        if end_newline: content += '\n'

        if cmd: content += ': '

        if flush: sys.stdout.flush()

        sys.stdout.write(content)

        if flush: sys.stdout.flush()

        return content

    def indicate(self, content, *, tag=1, cmd=True, replace=True, beg_newline=False, end_newline=False, flush=True, color=''):
        """Standard Indication Print Statement"""
        if self.client:
            if not self.client.terminal.enabled and cmd:
                cmd = False
                beg_newline = True

        return self.__print(content, tag=tag, cmd=cmd, replace=replace, beg_newline=beg_newline, end_newline=end_newline, flush=flush, color=color)

    def explain(self, content, *, tag=2, cmd=True, replace=True, beg_newline=False, end_newline=False, flush=True, color=''):
        """Print Statement meant to give extra information"""
        if self.client:
            if not self.client.terminal.enabled and cmd:
                cmd = False
                beg_newline = True

        return self.__print(content, tag=tag, cmd=cmd, replace=replace, beg_newline=beg_newline, end_newline=end_newline, flush=flush, color=color)

    def warning(self, content, *, tag=1, cmd=True, replace=True, beg_newline=False, end_newline=False, flush=True, color=colorama.Fore.RED):
        """Warning Print Statement"""
        if self.client:
            if not self.client.terminal.enabled and cmd:
                cmd = False
                beg_newline = True

        return self.__print(content, tag=tag, cmd=cmd, replace=replace, beg_newline=beg_newline, end_newline=end_newline, flush=flush, color=color)

    def success(self, content, *, tag=1, cmd=True, replace=True, beg_newline=False, end_newline=False, flush=True, color=colorama.Fore.GREEN):
        """Success Print Statement"""
        if self.client:
            if cmd and self.client.ready and not self.client.terminal.enabled:
                cmd = False
                beg_newline = True

        return self.__print(content, tag=tag, cmd=cmd, replace=replace, beg_newline=beg_newline, end_newline=end_newline, flush=flush, color=color)

    def cmd_return(self):
        return self.__print('', tag=3, cmd=False, replace=True, beg_newline=False, end_newline=False, flush=False, color='')


class Shutdown(Exception):
    """An Exception used to signal shutdown commands.  Should always be caught or passed on."""
    def __init__(self):
        Exception.__init__(self, 'An Exception used to signal shutdown commands.  Does not signify an error, although this should have been caught.')


class Restart(Exception):
    """An Exception used to signal restart commands.  Should always be caught or passed on."""
    def __init__(self):
        Exception.__init__(self, 'An Exception used to signal restart commands.  Does not signify an error, although this should have been caught.')


class ErrorRestart(Exception):
    """An Exception used to signal a bot issue.  Should always be caught or passed on."""
    def __init__(self):
        Exception.__init__(self, 'An Exception used to signal a bot issue.  Does not signify an error, although this should have been caught.')


class PIP(object):
    """A class to interact with PIP from within the python script."""

    @classmethod
    def works(cls):
        try:
            import pip
            return True
        except ImportError:
            return False

    @classmethod
    def run(cls, command, check_output=False):
        if not cls.works():
            raise RuntimeError("Could Not Import PIP.")

        try:
            return PIP.run_python_m(*command.split(), check_output=check_output)
        except subprocess.CalledProcessError as e:
            return e.returncode
        except:
            traceback.print_exc()
            print("Error running PIP with '-m' method.")

    @classmethod
    def run_python_m(cls, *args, **kwargs):
        check_output = kwargs.pop('check_output', False)
        check = subprocess.check_output if check_output else subprocess.check_call

        return check([sys.executable, '-m', 'pip'] + list(args))

    @classmethod
    def run_pip_main(cls, *args, **kwargs):
        import pip

        args = list(args)
        check_output = kwargs.pop('check_output', False)

        if check_output:
            from io import StringIO

            out = StringIO()
            sys.stdout = out

            try:
                pip.main(args)
            except:
                traceback.print_exc()
            finally:
                sys.stdout = sys.__stdout__

                out.seek(0)
                pipdata = out.read()
                out.close()

                print(pipdata)
                return pipdata
        else:
            return pip.main(args)

    @classmethod
    def run_install(cls, cmd, quiet=False, check_output=False):
        return cls.run("install %s%s" % ('-q ' if quiet else '', cmd), check_output)

    @classmethod
    def run_show(cls, cmd, check_output=False):
        return cls.run("show %s" % cmd, check_output)

    @classmethod
    def get_module_version(cls, mod):
        try:
            out = cls.run_show(mod, check_output=True)

            if isinstance(out, bytes):
                out = out.decode()

            datas = out.replace('\r\n', '\n').split('\n')
            expectedversion = datas[3]

            if expectedversion.startswith('Version: '):
                return expectedversion.split()[1]
            else:
                return [x.split()[1] for x in datas if x.startswith("Version: ")][0]
        except:
            pass
