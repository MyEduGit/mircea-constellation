#!/bin/bash
set -e

echo "Installing bcrypt..."
pip3 install bcrypt -q 2>/dev/null || apt-get install -y python3-bcrypt -q 2>/dev/null || true

echo "Generating password hash..."
HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'mircea8', bcrypt.gensalt(12)).decode())")

if [ -z "$HASH" ]; then
  echo "Python bcrypt failed, trying node path search..."
  BCRYPT_PATH=$(docker exec nemoclaw-n8n find /usr/local/lib -name "bcryptjs" -type d 2>/dev/null | head -1)
  HASH=$(docker exec nemoclaw-n8n node -e "const b=require('${BCRYPT_PATH}');console.log(b.hashSync('mircea8',10));")
fi

echo "Updating credentials in database..."
docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -c "UPDATE \"user\" SET email='mircea8@me.com', password='$HASH' WHERE email='mircea@nemoclaw.local';"

echo ""
echo "Done!"
echo "Email:    mircea8@me.com"
echo "Password: mircea8"
echo "URL:      http://localhost:5678"
