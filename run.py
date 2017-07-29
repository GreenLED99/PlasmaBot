import os
import gc
import sys
import time
import traceback
import subprocess
import importlib
import websockets

from plasmaBot import Printer, Shutdown, Restart, ErrorRestart, PIP

def sys_initialize():
    printer = Printer()
    printer.clear_screen()

    if not sys.version_info >= (3, 5):
        printer.warning('This version of Python is outdated.  (Required: \'3.5\', Current: \'{}\')'.format(sys.version.split()[0]))
        printer.indicate('Attempting to locate a newer version of Python...')

        pycom = None

        if sys.platform.startswith('win'):
            try:
                subprocess.check_output('py -3.5 -c "exit()"', shell=True)
                py_operator = 'py -3.5'
            except:
                try:
                    subprocess.check_output('py -3.6 -c "exit()"', shell=True)
                    py_operator = 'py -3.6'
                except:
                    try:
                        subprocess.check_output('python3 -c "exit()"', shell=True)
                        py_operator = 'python3'
                    except:
                        try:
                            subprocess.check_output('python3.5 -c "exit()"', shell=True)
                            py_operator = 'python3.5'
                        except:
                            try:
                                subprocess.check_output('python3.6 -c "exit()"', shell=True)
                                py_operator = 'python3.6'
                            except:
                                try:
                                    subprocess.check_output('python35 -c "exit()"', shell=True)
                                    py_operator = 'python35'
                                except:
                                    try:
                                        subprocess.check_output('python36 -c "exit()"', shell=True)
                                        py_operator = 'python36'
                                    except:
                                        pass

            if py_operator:
                printer.success('Sufficient Version of Python Found.  Restarting PlasmaBot using:\n      \'{} run.py\''.format(py_operator), tag=2)

                os.system('start cmd /k {} run.py'.format(py_operator))
                sys.exit(0)

        else:
            try:
                py_operator = subprocess.check_output(['which', 'python3.5']).strip().decode()
            except:
                pass

            if py_operator:
                printer.success('Sufficient Version of Python Found.  Restarting PlasmaBot using:\n      \'{} run.py\''.format(py_operator), tag=2)

                os.execlp(py_operator, py_operator, 'run.py')

        printer.warning('No sufficient version of Python found.  Please restart PlasmaBot using Python3.5 or greater.\n', tag=2)
        input(printer.Fore.MAGENTA + 'Press ENTER to continue...')

        return

    import asyncio

    t_req = False
    retry = True

    err_count = 0
    retry_pause = 45

    import plasmaBot

    while retry:

        try:
            importlib.reload(plasmaBot)
            bot = plasmaBot.Client(printer)
            bot.initiate()

        except (KeyboardInterrupt, SystemExit, plasmaBot.Shutdown):
            printer.indicate('Shutting Down...', cmd=False, beg_newline=True, end_newline=True, replace=False)

            try:
                bot.loop.run_until_complete(bot.logout())
            except:
                pass

            pending = asyncio.Task.all_tasks()
            gathered = asyncio.gather(*pending)

            try:
                gathered.cancel()
                bot.loop.run_until_complete(gathered)
                gathered.exception()
            except:
                pass

            break

        except SyntaxError:
            sys.stdout.write(printer.Style.RESET_ALL + printer.Fore.RED)
            traceback.print_exc()
            sys.stdout.write(printer.Style.RESET_ALL)
            break

        except ImportError as import_err:
            if not t_req:
                t_req = True

                printer.warning(import_err)
                printer.indicate('Attempting to install dependencies...')

                pip_error = PIP.run_install('--upgrade -r requirements.txt')

                if pip_error:
                    printer.warning('You should {} to manually install the Python Dependencies for PlasmaBot.'.format(['use \'sudo\'', 'run as administrator'][sys.platform.startswith('win')]))
                    break
                else:
                    printer.success('Successfully installed dependencies!')
            else:
                printer.warning('Unknown Import Error, Shutting Down...')
                break

        except Restart:
            printer.indicate('Restarting...', replace=False, beg_newline=True)
            err_count = -1

            try:
                bot.loop.run_until_complete(bot.logout())
            except:
                pass

            pending = asyncio.Task.all_tasks()
            gathered = asyncio.gather(*pending)

            try:
                gathered.cancel()
                asyncio.get_event_loop().run_until_complete(gathered)
                gathered.exception()
            except:
                pass

            time.sleep(0.75)

            try:
                gc.collect()
            except:
                pass

            try:
                kill_loop = asyncio.get_event_loop()
                kill_loop.call_soon_threadsafe(kill_loop.stop)
                kill_loop.close()
            except:
                pass

            os.execv(sys.executable, [__file__] + sys.argv)

        except ErrorRestart:
            try:
                bot.loop.run_until_complete(bot.logout())
            except:
                pass

            pending = asyncio.Task.all_tasks()
            gathered = asyncio.gather(*pending)

            try:
                gathered.cancel()
                asyncio.get_event_loop().run_until_complete(gathered)
                gathered.exception()
            except:
                pass

            time.sleep(0.75)

            try:
                gc.collect()
            except:
                pass

            try:
                kill_loop = asyncio.get_event_loop()
                kill_loop.call_soon_threadsafe(kill_loop.stop)
                kill_loop.close()
            except:
                pass

            os.execv(sys.executable, [__file__] + sys.argv)

        except Exception as other_err:
            sys.stdout.write(printer.Style.RESET_ALL + printer.Fore.RED)
            traceback.print_exc()
            sys.stdout.write(printer.Style.RESET_ALL)

            pending = asyncio.Task.all_tasks()
            gathered = asyncio.gather(*pending)

            try:
                gathered.cancel()
                asyncio.get_event_loop().run_until_complete(gathered)
                gathered.exception()
            except:
                pass

            time.sleep(0.75)

            try:
                gc.collect()
            except:
                pass

            try:
                kill_loop = asyncio.get_event_loop()
                kill_loop.call_soon_threadsafe(kill_loop.stop)
                kill_loop.close()
            except:
                pass

        finally:
            asyncio.set_event_loop(asyncio.new_event_loop())
            err_count += 1

        gc.collect()

        sleeptime = min(err_count * 2, retry_pause)
        if sleeptime:
            printer.warning('Restarting Code in {} seconds'.format(sleeptime))
            time.sleep(sleeptime)


if __name__ == '__main__':
    sys_initialize()
