#!/bin/bash
set -e
echo "Generating password hash..."
HASH=$(docker exec nemoclaw-n8n node -e "const b=require('bcryptjs');console.log(b.hashSync('mircea8',10));")
echo "Updating n8n credentials..."
docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -c "UPDATE \"user\" SET email='mircea8@me.com', password='$HASH' WHERE email='mircea@nemoclaw.local';"
echo ""
echo "Done! Login at http://localhost:5678"
echo "Email:    mircea8@me.com"
echo "Password: mircea8"
