# -*- coding: utf-8 -*-
import os
import abc
import subprocess
import logging
from glob import glob
from datetime import datetime, timedelta
import morumotto.toolbox as toolbox
from django.utils.crypto import get_random_string

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger = logging.getLogger('Plugins')


class SourcePlugin():
    """ This abstract class defines the methods for all sources



    To create a source plugin, create a file named
    plugins/structures/yoursource.py (with "yoursource" being the name of the
    srouce you want to use), in which you will write how this plugin fetches
    data, according to the plugins I/O standards for this software,
    and then in this file, create a new class that inherits from SourcePlugin,
    and define  :

    - the name to the plugin, e.g. :
        -> plugin_file = "yoursource.sh"
    - the name to the availability plugin, e.g. :
        -> avail_plugin_file = "yoursource_availability.sh"

    Then you need to instanciate the abstract method "set_connect_infos", e.g :

       -> def set_connect_infos(self,parameters,limit_rate):
            return "client:%s?limit-rate=%sk" % (parameters,limit_rate)

    You can have a look at the other existing class (FdsnWS, line 210 in this
    file for example) to see how to proceed
    """

    def __init__(self):
        self.script = os.path.join(
                    BASE_DIR, os.path.join("plugins", "sources",
                    str(self.plugin_file))
                    )
        self.avail_script = os.path.join(
                          BASE_DIR, os.path.join("plugins", "sources",
                          str(self.avail_plugin_file))
                          )

    def return_code_to_db(self, returncode, plugin_name):
        """
        Method which converts the outputs of the plugins into database
        readable messages.

        returncode must be a number between 0 and 5.
                0 : Success
                1 : Execution error
                2 : No data/inventory found
                3 : Timeout or connection error
                4 : Bad ID error
                5 : Writing error
        """
        if returncode == 0:
            logger.info("Plugin %s finished with success", plugin_name)
        elif returncode == 1:
            logger.warning("Plugin %s failed : Execution error. See PATCH log",
                           plugin_name)
        elif returncode == 2:
            logger.warning("Plugin %s failed : No Data Found", plugin_name)
        elif returncode == 3:
            logger.warning("Plugin %s failed : Timeout or Bad Request",
                            plugin_name)
        elif returncode == 1:
            logger.warning("Plugin %s failed: Bad ID error", plugin_name)
        elif returncode == 1:
            logger.warning("Plugin %s failed : Writing error", plugin_name)


    def read(self, postfile, workspace, data_format, blocksize,
             compression, connect_infos, cpu_limit, log, log_level=3):
        """ This method will call the plugin associated with this class.

        Parameters
        ----------
        nscl : `str`
               The Network/Station/Location/Channel code. Can be something like:
               RA.*.H??.00 for exemple
        starttime : `datetime`
                    The starting time of the data we want to collect
        end : `datetime`
                    The ending time of the data we want to collect
        workspace : `str`
                    The complete dir name where we are going to put the data
        data_format : `str`
                       The format we are using, eg. "seed"
        blocksize : `int`
                    The block size. Must be 2^N, between 256 and 8192
        compression : `str`
                    Valid formats are STEIM1, STEIM2, INT_16,
                    INT_32, INT_24, IEEE_FP_SP, IEEE_FP_DP
        connect_infos : `str`
                        This string will contain all the infos that will be
                        needed to connect to our device. It can be something
                        like ipadress:port?pwd=titi&?usr=toto?&bw_limit=50ko,
                        but it doesn't really matters as it is only important
                        that the plugin understands this str and all
                        informations required for the connection to the device
                        are in this str
        cpu_limit : `int`
                    Percentage of CPU allowed
        log : `str`
                    The complete log path to logfile
        """
        try:
            arg_list= ['--postfile={0}'.format(postfile),
                       '--workspace={0}'.format(workspace),
                       '--data-format={0}'.format(data_format),
                       '--blocksize={0}'.format(blocksize),
                       '--compression={0}'.format(compression),
                       '--connect-infos={0}'.format(connect_infos),
                       '--cpu-limit={0}'.format(cpu_limit),
                       '--log-level={0}'.format(log_level),
                       ]
            result = subprocess.run([self.script] + arg_list,
                                    stdout=subprocess.PIPE
                                    )
            logfile = open(log, 'a')
            logfile.write("%s" % result.stdout.decode('utf-8')+"\n")
            logfile.close()
            self.return_code_to_db(result.returncode, self.plugin_file)
            # print('return code : ', result.returncode)
            return result.returncode

        except (TypeError, IndexError, OSError) as err:
            logger.error(err)
            return err


    def availability(self, postfile, workspace, connect_infos, log, log_level=3):
        """
        This module must be able to create and update the inventory of our
        plugin
        """
        # print("postfile", postfile, " \n script ", self.avail_script)
        try:
            arg_list= ['--postfile={0}'.format(postfile),
                       '--workspace={0}'.format(workspace),
                       '--connect-infos={0}'.format(connect_infos),
                       '--log-level={0}'.format(log_level),
                       ]
            result = subprocess.run([self.avail_script] + arg_list,
                                    stdout=subprocess.PIPE)

            logfile = open(log, 'a')
            logfile.write("%s" % result.stdout.decode('utf-8')+"\n")
            logfile.close()
            self.return_code_to_db(result.returncode, self.avail_plugin_file)

            availability_file = postfile.replace("post.", "")
            if (result.returncode == 0):
                return availability_file
            else:
                return None

        except (TypeError, IndexError, OSError) as err:
            logger.error(err)
            return err


    def read_availability(self, line):
        """
        This methods returns nslc, starttime and endtime from an
        availability file
        """
        word = line.split()
        nslc_code = '{0}.{1}.{2}.{3}'.format(word[0],word[1],word[2],word[3])
        starttime = datetime.strptime(word[4], "%Y-%m-%dT%H:%M:%S.%fZ")
        endtime = datetime.strptime(word[5], "%Y-%m-%dT%H:%M:%S.%fZ")
        return nslc_code, starttime, endtime


    def is_online(self,parameters, log_level, log):
        """
        This module must be able to ask if a source is available
        """
        try:
            arg_list= ['--is_online={0}'.format(parameters),
                       '--log-level={0}'.format(log_level),
                       ]
            result = subprocess.run([self.script] + arg_list,
                                    stdout=subprocess.PIPE)
            try:
                logfile = open(log, 'a')
                logfile.write("%s" % result.stdout.decode('utf-8')+"\n")
                logfile.close()
            except (OSError) as err:
                logger.error(err)
                raise err
            if result.returncode == 0:
                return True
            else:
                return False

        except (TypeError, IndexError) as err:
            logger.error(err)
            return err


    @abc.abstractmethod
    def set_connect_infos(self, *args, **kwargs):
        """
        This module returns a string containing the infos to
        connect to the plugin
        """
        pass


class FdsnWS(SourcePlugin):
    """
    Class for the FDSN Web Service source plugin
    The plugin is plugins/fdsnws.sh
    """
    plugin_file = "fdsnws.sh"
    avail_plugin_file = "fdsnws_availability.sh"
    template = "client URL (ex: service.iris.edu)"

    def set_connect_infos(self,parameters,limit_rate):
        """
        returns a string containing the infos to connect to the fdsnws.sh plugin
        from the parameters and limit rate
        """
        return "client:%s?limit-rate=%sk" % (parameters,limit_rate)


class SSH_SDS(SourcePlugin):

    """
    Class for the plugin to connect a SDS archive accessible with SSH protocol
    The plugin is plugins/ssh_sds.sh
    """
    plugin_file = "ssh_sds.sh"
    avail_plugin_file = "ssh_sds_availability.sh"
    template = "ssh path (ex: user@server:/path/to/data)"

    def set_connect_infos(self,parameters,limit_rate):
        return "client:%s?limit-rate=%sk" % (parameters,limit_rate)


class LOCAL_DIR(SourcePlugin):

    """
    Class for the plugin to connect a SDS archive accessible with SSH protocol
    The plugin is plugins/local_dir.sh
    """
    plugin_file = "local_dir.sh"
    avail_plugin_file = "local_dir_availability.sh"
    template = "path&struct (ex : /final_archive&SDS )"
    def set_connect_infos(self,parameters,limit_rate):
        dir=parameters.split("&")[0]
        structure=parameters.split("&")[1]
        return "dir:%s&structure:%s?limit-rate=%sk" %(dir,structure,limit_rate)



class Q330S(SourcePlugin):
    plugin_file = "----"
    avail_plugin_file = "----"
    template = "Not implemented yet"

class Centaur(SourcePlugin):
    plugin_file = "----"
    avail_plugin_file = "----"
    template = "Not implemented yet"

class PCFox(SourcePlugin):
    plugin_file = "----"
    avail_plugin_file = "----"
    template = "Not implemented yet"
