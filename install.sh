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
  dep_list="python wget make pip mysql rabbitmq-server supervisor"
  read -p "${OS} found, do you want to install dependencies\
 automatically as sudo ? [(y)/n] > " answer
  if ! [[ "${answer}" =~ ^([Nn])+$ ]] ;then
    echo -e ", installing dependencies automatically :) "
    sudo apt-get install -y python wget make python-pip mysql-server \
    rabbitmq-server libmysqlclient-dev libpython3.6-dev supervisor ||\
    $(echo -e "\n ERROR: Can't install dependencies. \
    Either upgrade our system to a newer version or install manually. \
    See README.md"; exit)
  fi
elif [ ${os} == 'debian' ]; then
  dep_list="python wget make pip mariadb rabbitmq-server supervisor"
  read -p "${OS} found, do you want to install dependencies\
 automatically as sudo ? [(y)/n] > " answer
  if ! [[ "${answer}" =~ ^([Nn])+$ ]] ;then
    echo -e ", installing dependencies automatically :) "
    sudo apt-get install -y python wget make python-pip mariadb-dev \
    libmariadb-dev-compat libmariadb-dev python3-dev libpython3.6-dev \
    python3-venv supervisor ||\
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
  echo -e "\Qmerge not found in /usr/local/bin, installing"
  wget http://www.ncedc.org/qug/software/ucb/qmerge.2014.329.tar.gz --timeout=30 ||\
  echo -e "Can't install qmerge, please install it and re-run this script"
  tar -xzf qmerge.2014.329.tar.gz || exit
  cp qmerge/qmerge ${dir}/bin
else
  echo -e "\nINFO: qmerge already installed."
fi

if ! [ -x "$(command -v ${dir}/bin/sdrsplit)" ]; then
  echo -e "\sdrsplit not found in /usr/local/bin, installing"
  wget http://www.ncedc.org/qug/software/ucb/sdrsplit.2013.260.tar.gz --timeout=30 ||\
  echo -e "Can't install sdrsplit, please install it and re-run this script"
  tar -xzf sdrsplit.2013.260.tar.gz || exit
  cp sdrsplit/sdrsplit ${dir}/bin
else
  echo -e "\nINFO: sdrsplit already installed."
fi



#________________________CONFIGURE LEAP SECOND________________________#
if [ -z ${LEAPSECONDS} ]; then
  echo "export LEAPSECONDS='${dir}/leapsecond.list'" >> ${HOME}/.bashrc
fi

# if [[ ":$PATH:" == *":${dir}/bin:"* ]]; then
#  echo -e "\n${dir}/bin already in your PATH"
# else
#   echo -e "\nadding ${dir}/bin to your PATH"
#   echo 'export PATH="${dir}/bin:$PATH"' >> ${HOME}/.bash_functions
#   echo 'source ${dir}/.bash_functions' >> ${HOME}/.bashrc
#   source ${HOME}/.bash_functions
# fi

cd ${dir}
rm -r ${INSTALL_DIR}


#________________________INITIALIZE DATABASE________________________#
function database_help() {
  echo -e '\nPlease run the following commands in a mysql prompt with your access\n'
  echo "> CREATE DATABASE your_database_name;"
  echo "> CREATE USER 'your_user_name'@'localhost' IDENTIFIED BY 'your_password';"
  echo "> GRANT ALL PRIVILEGES ON your_database_name.* TO 'user_name'@'localhost';"
  echo "> FLUSH PRIVILEGES;"
  echo -e "\nWhen you are done, run this script again"
  exit
}

# Ask if user wants to initialize database in this script
read -p "Do you want to initialize the database now? [(y)/n] > " answer
if ! [[ "${answer}" =~ ^([Nn])+$ ]] ;then
  # ask if user already created a database and a user/password
  read -p "Did you already create a database and a user ? [(y)/n] > " answer
  if [[ "${answer}" =~ ^([Nn])+$ ]] ;then
    echo -e "\nOK, I will try to create them for you then !"
    echo -e "\nPlease enter root user MySQL password:"
    read -s rootpasswd

    if ! mysql -u root -p${rootpasswd}  -e ";" ;then
      echo "ERROR : Seems that I can't access to your root account for mysql."
      database_help
    else
      read -p "Enter a DATABASE name > " DB_NAME
      read -p "Enter a USER name for your database > " USER_NAME
      while true; do
        read -s -p "Enter a PASSWORD for your user: " PASSWD
        echo
        read -s -p "Confirm password: " PASSWD2
        echo
        [ "$PASSWD" = "$PASSWD2" ] && break
        echo "Passwords didn't match, try again."
      done
      mysql -uroot -p${rootpasswd} -e "CREATE DATABASE ${DB_NAME};"
      mysql -uroot -p${rootpasswd} -e "CREATE USER ${USER_NAME}@localhost IDENTIFIED BY '${PASSWD}';"
      mysql -uroot -p${rootpasswd} -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${USER_NAME}'@'localhost';"
      mysql -uroot -p${rootpasswd} -e "FLUSH PRIVILEGES;"
    fi
  else
    read -p "Enter your DATABASE name > " DB_NAME
    read -p "Enter your USER name for ${DB_NAME} > " USER_NAME
    read -s -p "Enter PASSWORD for ${USER_NAME} > " PASSWD
    if ! mysql -u ${USER_NAME} -p ${PASSWD}  -e ";" ;then
      echo -e "\n ERROR : Seems that you didn't initialize the ${DB_NAME} database with ${USER_NAME}, or your password was wrong,"
      database_help
    fi
    read -p "Enter your DATABASE HOST (leave empty to use default : '127.0.0.1') > " DB_HOST
    if [ -z ${DB_HOST} ]; then
      DB_HOST='127.0.0.1'
    fi
  fi
  # Create the custom setting file for your database
  if ! mysql -u ${USER_NAME} -p${PASSWD}  -e ";" ;then
    echo -e "\n ERROR: your database was not initialized correctly"
    database_help
  else
    [ -e ${dir}/siqaco/custom_settings.py ] && rm ${dir}/siqaco/custom_settings.py
    echo "# Enter your own settings here" >> ${dir}/custom_settings.py
    echo "DATABASE_ENGINE = 'django.db.backends.mysql'" >> ${dir}/custom_settings.py
    echo "DATABASE_NAME = '${DB_NAME}'" >> ${dir}/custom_settings.py
    echo "DATABASE_USER_NAME = '${USER_NAME}'" >> ${dir}/custom_settings.py
    echo "DATABASE_PASSWORD = '${PASSWD}'" >> ${dir}/custom_settings.py
    echo "DATABASE_HOST = '${DB_HOST}'" >> ${dir}/custom_settings.py
    mv ${dir}/custom_settings.py ${dir}/siqaco/custom_settings.py || exit
    echo -e "\n Database initialized correctly, settings are saved in ${dir}/siqaco/custom_settings.py \n"
  fi
fi

#________________________CHECK CUSTOM SETTINGS FILE________________________#
if ! [[ -e ${dir}/siqaco/custom_settings.py ]]; then
  echo -e "\nERROR: file siqaco/custom_settings.py not found \nPlease create this\
file and copy paste the follwing lines inside (change the fields with your\
own informations): \n\n\
DATABASE_ENGINE = 'django.db.backends.mysql'\n\
DATABASE_NAME = 'your_database_name' \n\
DATABASE_USER_NAME = 'your_user_name'\n\
DATABASE_PASSWORD = 'your_password'\n\n\
OR, run this script again and accept to initialize the database"
  exit
fi

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
    echo -e "\npip install virtualenv"
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
pip install -r requirements.txt || (echo -e "\Error while installing project's \
python requirements. Possibly missing dependencies. Try : \n \
sudo apt install libmysqlclient-dev libpython3.6-dev  \n \
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
python manage.py makemigrations seismicarchive monitoring qualitycontrol logdb || exit
python manage.py migrate || exit

#________________________DEAMONIZE WITH SUPERVISOR________________________#
echo -e "\nCreating supervisor configuration file"

cat <<EOT >> morumotto.conf
[program:morumotto_celery]
command = ${dir}/morumotto-env/bin/celery -A siqaco worker -l info
user = ${USER}
directory = ${dir}
logfile = /var/log/supervisor/morumotto_celery.log
logfile_maxbytes = 50MB
logfile_backups=10
loglevel = info
autostart = true
autorestart = true

[program:morumotto_flower]
command = ${dir}/morumotto-env/bin/celery flower -A siqaco --address=127.0.0.1 --port=5555
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
