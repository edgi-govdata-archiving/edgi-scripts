#!/bin/bash

# Adapted from: https://gist.github.com/steverobbins/11bac3bc5d3b6156e634d9aaf30978bd
# Save all URLS from a website to Wayback Save Page Now
URL=$1
PATH=$2
EXCLUDE=$3

TMP_PATH=$(/bin/mktemp --directory)

echo "Gathering URLs..."

/usr/bin/wget --quiet --recursive --no-clobber "$URL$PATH" \
  --domains "$URL" \
  --directory-prefix "$TMP_PATH" \
  --exclude-directories "$EXCLUDE" \
  --accept html

echo "Sending to archive.org..."

/usr/bin/find "$TMP_PATH" -type f -print0 | while IFS= read -r -d $'\0' LINE; do
    LINE=$(echo $LINE | /bin/sed -e 's/\(index.html\)*$//g')
    echo "Saving $LINE"
    /usr/bin/curl -s "https://web.archive.org/save/$LINE" > /dev/null &
    /bin/sleep 1
done

echo "Done"

/bin/rm -rf "$TMP_PATH"
