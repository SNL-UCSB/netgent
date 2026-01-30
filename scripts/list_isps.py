import os

def list_isps():
    isp_dir = "examples/isps"
    isps = []
    
    # Iterate through files in the directory
    for filename in os.listdir(isp_dir):
        if filename.endswith(".py") and filename != "__init__.py" and not filename.startswith("bulk_update"):
            # Remove extension to get ISP name
            isp_name = filename[:-3]
            isps.append(isp_name)
            
    # Sort for consistent output
    isps.sort()
    
    print(f"Found {len(isps)} ISPs configured in {isp_dir}:")
    for isp in isps:
        print(f"- {isp}")

if __name__ == "__main__":
    list_isps()
