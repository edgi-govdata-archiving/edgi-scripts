#!/bin/bash

# Adapted from: https://gist.github.com/steverobbins/11bac3bc5d3b6156e634d9aaf30978bd

URL=$1
PATH=$2
EXCLUDE=$3

/bin/rm -rf "$URL"

echo "Gathering URLs..."

/usr/bin/wget -q -r -nc "$URL$PATH" -D "$URL" -X "$EXCLUDE" -A html

echo "Sending to archive.org..."

/usr/bin/find "$URL" -type f -print0 | while IFS= read -r -d $'\0' LINE; do
    LINE=$(echo $LINE | /bin/sed -e 's/\(index.html\)*$//g')
    echo "Saving $LINE"
    /usr/bin/curl -s "https://web.archive.org/save/$LINE" > /dev/null &
    /bin/sleep 1
done

echo "Done"

/bin/rm -rf "$URL"
