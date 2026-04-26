#!/bin/bash
# Install OffGrid daily pipeline as a launchd job (Mac native cron alternative)
PLIST=~/Library/LaunchAgents/com.offgrid.dailypipeline.plist
cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.offgrid.dailypipeline</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/gauravoffgrid/offgrid-marketing-os/scripts/cron_daily_pipeline.sh</string>
        <string>askgauravai</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>8</integer>
        <key>Minute</key><integer>0</integer>
    </dict>
    <key>StandardOutPath</key><string>/tmp/grid_launchd.log</string>
    <key>StandardErrorPath</key><string>/tmp/grid_launchd_err.log</string>
</dict>
</plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "✅ launchd job installed: com.offgrid.dailypipeline"
echo "   Runs daily at 8:00am local time"
echo "   View logs: tail -f /tmp/grid_launchd.log"
