# Authentication Setup Guide

## Your Generated Token
```
MCP_AUTH_TOKEN: 0USbNEFqvtn3cWCmj4KsVwyrH598QDZh
```

⚠️ **IMPORTANT**: Keep this token secret! Treat it like a password.

## Step-by-Step Setup

### 1. Configure Render Environment Variables

Go to: https://dashboard.render.com/
Navigate to: Your Service → Environment

Add these variables:
```
MCP_AUTH_TOKEN=0USbNEFqvtn3cWCmj4KsVwyrH598QDZh
ENVIRONMENT=production
```

### 2. Wait for Redeploy
Render will automatically redeploy after you save the environment variables.
Check the deploy logs to ensure it started successfully.

### 3. Configure Poke

In Poke settings (https://poke.com/settings/connections):

**If Poke supports headers:**
- URL: `https://your-service-name.onrender.com/mcp`
- Add custom header: `Authorization: Bearer 0USbNEFqvtn3cWCmj4KsVwyrH598QDZh`

**If Poke only supports URL-based auth:**
- URL: `https://your-service-name.onrender.com/mcp?auth=0USbNEFqvtn3cWCmj4KsVwyrH598QDZh`

### 4. Test the Connection

After configuring, test in Poke:
1. Send: `clearhistory` (to reset any cached connections)
2. Try: "Show all Trello boards I have access to"
3. If it works, you're all set!

## Troubleshooting

### If authentication fails:
1. Check Render logs for errors
2. Verify the token is set correctly in Render
3. Make sure ENVIRONMENT=production is set
4. Try the test script: `.\test_auth.ps1`

### If Poke can't connect:
1. Verify the URL ends with `/mcp`
2. Check if Poke requires a specific auth format
3. Try both header and URL-based authentication methods

## Security Notes

- Never share your MCP_AUTH_TOKEN publicly
- Rotate the token periodically (regenerate and update)
- Monitor Render logs for unauthorized access attempts
- Consider IP whitelisting if Render supports it

## Regenerating Token

If you need a new token:
```powershell
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

Then update it in:
1. Render environment variables
2. Poke connection settings
3. This documentation