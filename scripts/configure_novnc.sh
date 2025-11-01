#!/usr/bin/env bash
# Configure noVNC to auto-connect

if [ -f /opt/noVNC/vnc.html ]; then
    # Enable auto-connect
    python3 << 'EOF'
import re

with open('/opt/noVNC/vnc.html', 'r') as f:
    content = f.read()

# Set autoConnect to true
content = re.sub(r'UI\.autoConnect\s*=\s*false', 'UI.autoConnect = true', content)
content = re.sub(r'UI\.autoConnect\s*=\s*[^;]+', 'UI.autoConnect = true', content)

# Add auto-connect call after UI initialization
if 'UI.connect();' not in content:
    # Add auto-connect after window load event
    if 'window.addEventListener("load"' in content:
        content = content.replace(
            'window.addEventListener("load"',
            'window.addEventListener("load"'
        )
        # Add setTimeout to call connect after UI is ready
        connect_code = '''
        setTimeout(function() {
            if (typeof UI !== "undefined" && typeof UI.connect === "function") {
                UI.connect();
            }
        }, 1000);
        '''
        # Insert before </body> tag
        if '</body>' in content:
            content = content.replace('</body>', '<script>' + connect_code + '</script></body>')
        elif '</html>' in content:
            content = content.replace('</html>', '<script>' + connect_code + '</script></html>')

with open('/opt/noVNC/vnc.html', 'w') as f:
    f.write(content)

print("noVNC configured for auto-connect")
EOF
else
    echo "Warning: /opt/noVNC/vnc.html not found"
fi

