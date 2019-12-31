#!/bin/bash
if [ "$EUID" -eq 0 ]; then
  echo "Please don't run this script as root"
  exit 1
fi

dir=$(pwd)

echo -e "Checking dependencies\n"
INSTALL_DIR=$(mktemp -d)
cd ${INSTALL_DIR}

#________________________CHECK OS VERSION________________________#
# This installer only works with Ubuntu >= 18.04 LTS and Debian >= 9
if [ -f /etc/os-release ]; then
  . /etc/os-release
  OS=$NAME
  VER=$VERSION_ID
elif type lsb_release >/dev/null 2>&1; then
  OS=$(lsb_release -si)
  VER=$(lsb_release -sr)
fi
os=$(echo $OS | awk -F '[ ]' '{print tolower($1)}')

if [[ ${os} == 'ubuntu' && ${VER} < 16.10 ]]; then
  echo -e "\n ERROR : Ubuntu version < 16.10"
  echo -e "This installer will probably not work and you need to\
  install manually or upgrade your system (recommanded). See README.md"
  exit
elif [[ ${os} == 'debian' && ${VER} < 9 ]]; then
  echo -e "\n ERROR : Debian version < 9"
  echo -e "This installer will probably not work and you need to\
  install manually or upgrade your system (recommanded). See README.md"
  exit
fi

#________________________INSTALL DEPENDENCIES________________________#
if [ ${os} == 'ubuntu' ]; then
  dep_list="python wget make pip rabbitmq-server supervisord java"
  read -p "${OS} found, do you want to install dependencies\
 automatically as sudo ? [(y)/n] > " answer
  if ! [[ "${answer}" =~ ^([Nn])+$ ]] ;then
    echo -e ", installing dependencies automatically :) "
    sudo apt-get install -y wget make python-pip default-jre \
    rabbitmq-server libpython3.6-dev supervisor cpulimit libssl-dev ||\
    $(echo -e "\n ERROR: Can't install dependencies. \
    Either upgrade our system to a newer version or install manually. \
    See README.md"; exit)
  fi
elif [ ${os} == 'debian' ]; then
  dep_list="python wget make pip rabbitmq-server supervisord default-jre"
  read -p "${OS} found, do you want to install dependencies\
 automatically as sudo ? [(y)/n] > " answer
  if ! [[ "${answer}" =~ ^([Nn])+$ ]] ;then
    echo -e ", installing dependencies automatically :) "
    sudo apt-get install -y wget make python-pip default-jre \
    python3-dev libpython3.6-dev libssl-dev\
    python3-venv supervisor cpulimit ||\
    $(echo -e "\n ERROR: Can't install dependencies. \
    Either upgrade our system to a newer version or install manually. \
    See README.md"; exit)
  fi
fi


#________________________CHECK DEPENDENCIES________________________#

continue=1

for dep in ${dep_list}; do
  if ! [ -x "$(command -v ${dep})" ]; then
    echo -e "ERROR: ${dep} not found"
    echo -e "Please install ${dep}"
    continue=0
  fi
done
if [ ${continue} -eq 0 ]; then
  exit
fi

mkdir -p ${dir}/bin

#________________________SPECIFIC TOOLS INSTALL________________________#
# Installing dataselect, qmerge, sdrsplit & msi

if ! [ -x "$(command -v ${dir}/bin/dataselect)" ]; then
  echo -e "\nDataselect not found in ${dir}/bin, installing"
  wget https://github.com/iris-edu/dataselect/archive/v3.21.tar.gz --timeout=30 || exit
  tar -xzf v3.21.tar.gz || exit
  cd dataselect-3.21
  make || exit
  make install || exit
  cp dataselect ${dir}/bin
else
  echo -e "\nINFO: dataselect already installed"
fi

if ! [ -x "$(command -v ${dir}/bin/msi)" ]; then
  echo -e "\nMSI not found in ${dir}/bin, installing"
  wget https://github.com/iris-edu/msi/archive/v3.8.tar.gz --timeout=30 || exit
  tar -xzf v3.8.tar.gz || exit
  cd msi-3.8
  make || exit
  make install || exit
  cp msi ${dir}/bin
else
  echo -e "\nINFO: msi already installed"
fi

if ! [ -x "$(command -v ${dir}/bin/qmerge)" ]; then
  echo -e "\nQmerge not found in ${dir}/bin, installing"
  wget http://www.ncedc.org/qug/software/ucb/qmerge.2014.329.tar.gz --timeout=30 ||\
  echo -e "Can't install qmerge, please install it and re-run this script"
  tar -xzf qmerge.2014.329.tar.gz || exit
  cp qmerge/qmerge ${dir}/bin
else
  echo -e "\nINFO: qmerge already installed."
fi

if ! [ -x "$(command -v ${dir}/bin/sdrsplit)" ]; then
  echo -e "\nsdrsplit not found in ${dir}/bin, installing"
  wget http://www.ncedc.org/qug/software/ucb/sdrsplit.2013.260.tar.gz --timeout=30 ||\
  echo -e "Can't install sdrsplit, please install it and re-run this script"
  tar -xzf sdrsplit.2013.260.tar.gz || exit
  cp sdrsplit/sdrsplit ${dir}/bin
else
  echo -e "\nINFO: sdrsplit already installed."
fi

if ! [[ -h "${dir}/bin/stationxml-validator.jar" ]]; then
  echo -e "\stationxml-validator not found in ${dir}/bin, installing"
  wget https://github.com/iris-edu/stationxml-validator/releases/download/1.6.0.2/stationxml-validator-1.6.0.2-SNAPSHOT.jar --timeout=30 &&\
  wget https://github.com/iris-edu/stationxml-validator/releases/download/1.5.9.5/station-xml-validator-1.5.9.5.jar --timeout=30 ||\
  echo -e "Can't install stationxml-validator, please install it and re-run this script"
  mv stationxml-validator-1.6.0.2-SNAPSHOT.jar ${dir}/bin
  mv station-xml-validator-1.5.9.5.jar ${dir}/bin
  ln -s ${dir}/bin/station-xml-validator-1.5.9.5.jar ${dir}/bin/stationxml-validator.jar
else
  echo -e "\nINFO: stationxml-validator already installed."
fi


#________________________CONFIGURE LEAP SECOND________________________#
if [ -z ${LEAPSECONDS} ]; then
  echo "export LEAPSECONDS='${dir}/leapsecond.list'" >> ${HOME}/.bashrc
fi

cd ${dir}
rm -r ${INSTALL_DIR}


#________________________INITIALIZE DATABASE________________________#
function database_help() {
  local DBM=$1
  if [ ${DBM} = 'mysql' ]; then
    echo -e '\nPlease run the following commands in a mysql prompt\n'
    echo "> CREATE DATABASE your_database_name;"
    echo "> CREATE USER 'your_user_name'@'localhost' IDENTIFIED BY 'your_password';"
    echo "> GRANT ALL PRIVILEGES ON your_database_name.* TO 'user_name'@'localhost';"
    echo "> ALTER DATABASE `MORUMOTTO` CHARACTER SET utf8;"
    echo "> FLUSH PRIVILEGES;"
  elif [ ${DBM} = 'postgresql' ]; then
    echo -e '\nPlease run the following commands in a postgresql prompt\n'
    echo "> CREATE DATABASE your_database_name;"
    echo "> CREATE USER your_user_name WITH ENCRYPTED PASSWORD 'your_password';"
    echo "> ALTER ROLE your_user_name SET default_transaction_isolation TO 'read committed';"
    echo "> ALTER ROLE your_user_name SET timezone TO 'UTC';"
    echo "> GRANT ALL PRIVILEGES ON DATABASE your_database_name to your_user_name;"
  fi
  echo -e "\nWhen you are done, run this script again"
  exit
}

# Ask if user wants to initialize database in this script
read -p "Do you want to initialize the database now? [(y)/n] > " answer
if ! [[ "${answer}" =~ ^([Nn])+$ ]] ;then
  while true; do
    read -p "Choose your database manager (M for mysql/mariadb, P for PostgreSQL) ? > " mp
      case ${mp} in
        [Mm]* ) RDBMS="mysql"; break;;
        [Pp]* ) RDBMS="postgresql"; break;;
        * ) echo "Please answer M or P.";;
      esac
  done

  # ask for database settings
  read -p "Enter your DATABASE name > " DB_NAME
  read -p "Enter your USER name for ${DB_NAME} > " USER_NAME
  read -s -p "Enter PASSWORD for ${USER_NAME} > " PASSWD
  echo ""
  read -p "Enter your DATABASE HOST (leave empty to use default : '127.0.0.1') > " DB_HOST
  if [ -z ${DB_HOST} ]; then
    DB_HOST='127.0.0.1'
  fi

  # Check database credentials
  if [ ${RDBMS} = 'mysql' ]; then
    if ! mysql -u ${USER_NAME} -p${PASSWD}  -e ";" ; then
      echo -e "\n ERROR : Seems that you didn't initialize the ${DB_NAME} database with ${USER_NAME}, or your password was wrong,"
      database_help ${RDBMS}
    fi
  elif [ ${RDBMS} = 'postgresql' ]; then
    if ! PGPASSWORD=${PASSWD} psql -U ${USER_NAME} -h ${DB_HOST} -d ${DB_NAME} -c '\q'; then
      echo -e "\n ERROR : Seems that you didn't initialize the ${DB_NAME} database with ${USER_NAME}, or your password was wrong,"
      database_help ${RDBMS}
    fi
  fi


  # Create the custom setting file for your database
  if [ -e ${dir}/morumotto/custom_settings.py ]; then
   rm ${dir}/morumotto/custom_settings.py
   touch ${dir}/morumotto/custom_settings.py
  fi
  echo "# Enter your own settings here" >> ${dir}/morumotto/custom_settings.py
  if [ ${RDBMS} = 'mysql' ]; then
    echo "DATABASE_ENGINE = 'django.db.backends.mysql'" >> ${dir}/morumotto/custom_settings.py
    echo 'OPTIONS = {"charset": "utf8", "init_command": "SET foreign_key_checks = 0;"}' >> ${dir}/morumotto/custom_settings.py
  elif [ ${RDBMS} = 'postgresql' ]; then
    echo "DATABASE_ENGINE = 'django.db.backends.postgresql'" >> ${dir}/morumotto/custom_settings.py
  fi
  echo "DATABASE_NAME = '${DB_NAME}'" >> ${dir}/morumotto/custom_settings.py
  echo "DATABASE_USER_NAME = '${USER_NAME}'" >> ${dir}/morumotto/custom_settings.py
  echo "DATABASE_PASSWORD = '${PASSWD}'" >> ${dir}/morumotto/custom_settings.py
  echo "DATABASE_HOST = '${DB_HOST}'" >> ${dir}/morumotto/custom_settings.py
  echo "CUSTOM_HOSTS = []" >> ${dir}/morumotto/custom_settings.py
  echo -e "\n Database initialized correctly, settings are saved in ${dir}/morumotto/custom_settings.py \n"
fi

#________________________CHECK CUSTOM SETTINGS FILE________________________#
if ! [[ -e ${dir}/morumotto/custom_settings.py ]]; then
    echo -e "\nERROR: file morumotto/custom_settings.py not found \nPlease create this\
file and copy paste the follwing lines inside (change the fields with your\
own informations): \n"
  if [ ${RDBMS} = 'mysql' ]; then
    echo -e "DATABASE_ENGINE = 'django.db.backends.mysql'\n"
    echo -e "OPTIONS = {'charset': 'utf8', 'init_command': 'SET foreign_key_checks = 0;'}"
  else
    echo -e "DATABASE_ENGINE = 'django.db.backends.postgresql'\n"
  fi
  echo -e "DATABASE_NAME = 'your_database_name' \n\
DATABASE_USER_NAME = 'your_user_name'\n\
DATABASE_PASSWORD = 'your_password'\n\
DATABASE_HOST = '127.0.0.1'\n\
CUSTOM_HOSTS = []\n\
OR, run this script again and accept to initialize the database"
  exit
fi
exit
#________________________CREATE VIRTUAL ENV________________________#
echo -e "\nCreating python virtual environment\n"
# Installing virtualenv
SYS_PYTHON_VERSION=$(python -c 'import sys; \
print(".".join(map(str, sys.version_info[:2])))' 2>&1)
echo -e "\nPython found, version: ${SYS_PYTHON_VERSION}"
if [[ "${SYS_PYTHON_VERSION}" < 3.3 ]]; then
  if ! [ -x "$(command -v virtualenv)" ]; then
    echo -e "ERROR: virtualenv command not found"
    echo -e "Please install virtualenv !"
    echo -e "To install as root : "
    echo -e "\napt install virtualenv"
    exit
  else
    virtualenv morumotto-env -p python3.6
  fi
else
  python -m venv morumotto-env || exit
fi

if ! [[ -d  "${dir}/morumotto-env" ]]; then
  echo -e "\n ERROR : failed to create virtual environment."
  echo -e "\n Exiting...\n"
  exit
fi;

#________________________INSTALL PYTHON DEP________________________#
source morumotto-env/bin/activate
pip install numpy==1.16.4 || exit
# Due to a bug in obspy setup.py, we need to install numpy first
pip install -q -r requirements.txt || (echo -e "\Error while installing project's \
python requirements. Possibly missing dependencies. Try : \n \
sudo apt install libmysqlclient-dev libpython3.6-dev libssl-dev  \n \
\n and execute installer again.\
\nExiting."; exit 1);

#________________________FILL DATABASE WITH DJANGO________________________#
python manage.py migrate || exit

#________________________CREATE ADMIN USER________________________#
read -p "Do you want to create an administrator user now? [(y)/n] > " answer
if ! [[ "${answer}" =~ ^([Nn])+$ ]] ;then
  echo -e "\nYou will now create the administrator of MORUMOTTO, don't forget \
  the password your will enter !\n"
  python manage.py createsuperuser || exit
else
  echo -e "\nYou can do it later by running 'python manage.py createsuperuser'"
fi

#________________________CREATE ALL FIELDS IN DATABASE________________________#
python manage.py makemigrations archive monitoring qualitycontrol logdb || exit
python manage.py migrate django_celery_results || exit
python manage.py migrate || exit

#________________________DEAMONIZE WITH SUPERVISOR________________________#
echo -e "\nCreating supervisor configuration file"

cat <<EOT >> morumotto.conf
[program:morumotto_celery]
command = ${dir}/morumotto-env/bin/celery -A morumotto worker -l info
user = ${USER}
directory = ${dir}
logfile = /var/log/supervisor/morumotto_celery.log
logfile_maxbytes = 50MB
logfile_backups=10
loglevel = info
autostart = true
autorestart = true

[program:morumotto_flower]
command = ${dir}/morumotto-env/bin/celery flower -A morumotto --address=127.0.0.1 --port=5555
user = ${USER}
directory = ${dir}
logfile = /var/log/supervisor/morumotto_flower.log
logfile_maxbytes = 50MB
logfile_backups=10
loglevel = info
autostart = true
autorestart = true

[program:morumotto_runserver]
command = ${dir}/morumotto-env/bin/python manage.py runserver 0.0.0.0:8000
user = ${USER}
directory = ${dir}
logfile = /var/log/supervisor/morumotto_runserver.log
logfile_maxbytes = 50MB
logfile_backups=10
loglevel = info
autostart = true
autorestart = true

[group:morumotto]
programs=morumotto_celery,morumotto_flower,morumotto_runserver
priority=999

EOT
echo -e "\nmorumotto.conf created. \nMoving it to /etc/supervisor/conf.d/"
sudo mv morumotto.conf /etc/supervisor/conf.d/ || exit
sudo supervisorctl reread
sudo supervisorctl update

#________________________INSTALL COMPLETE !________________________#
echo -e "\nInstallation complete ! You can now use MORUMOTTO ! "
echo -e "\nTo get started, visit http://127.0.0.1:8000/home/  \nBye !\n"
