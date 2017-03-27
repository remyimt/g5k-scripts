SITE=$1

apt-get update && apt-get -y dist-upgrade
debconf-set-selections <<< 'mysql-server mysql-server/root_password password strangehat'
debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password strangehat'
apt-get -y install mysql-server python python-mysqldb python-pip vim
pip install execo httplib2 pysnmp
mysql -uroot -pstrangehat -Ne "CREATE DATABASE pdu"
mysql -uroot -pstrangehat pdu -Ne "CREATE TABLE monitoring (timestamp BIGINT, uid VARCHAR(300), \
  outlet VARCHAR(300), value BIGINT);"
./pdu-generator.py $SITE
./metrics-pdu.py $SITE
