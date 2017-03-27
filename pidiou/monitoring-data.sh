#!/bin/bash

NODE_NAME=$1
SITE='nancy'
DATE=$(date +%F-%Hh)
DUMP_FOLDER='dumps'

if [ -d $DUMP_FOLDER ]; then
  mkdir $DUMP_FOLDER
fi
ssh root@$NODE_NAME "mysqldump -uroot -pstrangehat pdu > $DATE-$SITE.db"
scp root@$NODE_NAME:$DATE-$SITE.db $DUMP_FOLDER
