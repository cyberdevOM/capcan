import os, json, shutil, subprocess
from datetime import datetime
from pathlib import Path



class Build_client():
    def __init__(self):
        # Ensure the build output directory exists
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # builder path
        self.CLIENT_TEMPLATE_DIR = os.path.normpath(os.path.join(self.BASE_DIR, "..", "client_template")) # template path
        self.BUILD_OUTPUT_DIR = os.path.normpath(os.path.join(self.BASE_DIR, "..", "builds"))
        self.config = None

    def load_config(self):
        config_path = os.path.join(self.CLIENT_TEMPLATE_DIR,"config.json")
        print(config_path)

        with open(config_path) as f:
            self.config = json.load(f)
    
    def build_deb_package(self, build_dir, client_id):
        print("[*] Creating .deb package...")
        # Create directory structure for .deb package
        deb_root = os.path.join(build_dir, "deb_root")
        os.makedirs(os.path.join(deb_root, "usr", "local", "bin"), exist_ok=True)
        shutil.copy(os.path.join(build_dir, "client_main"), os.path.join(deb_root, "usr", "local", "bin", f"{client_id}"))

        # Control file
        control_dir = os.path.join(deb_root, "DEBIAN")
        os.makedirs(control_dir, exist_ok=True)
        control_content = f"""Package: {client_id}
Version: 1.0
Section: base
Priority: optional
Architecture: amd64
Maintainer: Tester@Capcan.com
Description: Honeypot client {client_id}
"""
        # Remove leading whitespace
        with open(os.path.join(control_dir, "control"), "w") as f:
            f.write(control_content)

        # Build .deb
        deb_path = os.path.join(build_dir, f"{client_id}.deb")
        subprocess.run(["dpkg-deb", "--build", deb_root, deb_path])
        print(f"[+] .deb package created at {deb_path}")
        
        # clean up: remove temporary directories
        for item in os.listdir(build_dir):
            item_path = os.path.join(build_dir, item)
            if item_path != deb_path:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        
        return deb_path

    def build_rpm_package(self, build_dir, client_id):
        print("[*] Creating .rpm package...")
        # Create directory structure for .rpm package
        rpm_build_dir = os.path.expanduser("~/rpmbuild")
        bin_dir = os.path.join(rpm_build_dir, "BUILDROOT", f"{client_id}-1.0-1.x86_64", "usr", "local", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy(os.path.join(build_dir, "client_main"), os.path.join(bin_dir, client_id))
        # Create RPM spec file
        spec_dir = os.path.join(rpm_build_dir, "SPECS")
        os.makedirs(spec_dir, exist_ok=True)
        spec_content = f"""Name: {client_id}
Version: 1.0
Release: 1%{{?dist}}
Summary: Honneypot client
License: MIT
BuildArch: x86_64

%description
Honeypot client binary

%prep
%build

%install
mkdir -p %{buildroot}/usr/local/bin
install -m 755 {client_id} %{buildroot}/usr/local/bin/{client_id}

%files
/usr/local/bin/{client_id}
        """
        
        # Remove leading whitespace
        spec_path = os.path.join(spec_dir, f"{client_id}.spec")
        with open(spec_path, "w") as f:
            f.write(spec_content)

        # Build RPM
        subprocess.run(["rpmbuild", "-bb", spec_path])
        rpm_path = os.path.join(rpm_build_dir, "RPMS", "x86_64", f"{client_id}-1.0-1.x86_64.rpm")
        if os.path.exists(rpm_path):
            print(f"[+] .rpm package created at {rpm_path}")
            # clean up: remove temporary directories
            final_rpm_path = os.path.join(build_dir, f"{client_id}.rpm")
            shutil.move(rpm_path, final_rpm_path)
            for item in os.listdir(build_dir):
                item_path = os.path.join(build_dir, item)
                if item_path != final_rpm_path:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)

            return rpm_path
        else:
            print("[!] RPM build failed - check rpmbuild logs.")
            return None

    def build(self, config):

        # define client config data
        client_id = config["client_id"]
        # server_url = config["server_url"]
        # watch_dirs = config["watch_dirs"]
        platform = config["platform"]

        # generate timestamped build directory
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        build_id = f"{client_id}_{timestamp}"
        build_dir = os.path.join(self.BUILD_OUTPUT_DIR, build_id)
        os.makedirs(build_dir, exist_ok=True)

        # copy entire client template into the build directory
        shutil.copytree(self.CLIENT_TEMPLATE_DIR, build_dir, dirs_exist_ok=True)

        # build binary using PyInstaller
        pyinstaller_cmd = [
            "pyinstaller",
            "--onefile",
            "--distpath", build_dir,
            "--workpath", os.path.join(build_dir, "build"),
            "--specpath", os.path.join(build_dir, "spec"),
            os.path.join(build_dir, "client_main.py")
        ]
        result = subprocess.run(pyinstaller_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[!] Build failed: {result.stderr}")
            return None
        
        binary_path = os.path.join(build_dir, "client_main")
        if not os.path.exists(binary_path):
            print("[!] Built binary not found") ##! important 
            return None
        
        if platform == "deb":
            return self.build_deb_package(build_dir, client_id)
        elif platform == "rpm":
            return self.build_rpm_package(build_dir, client_id)
        else:
            print(f"[!] Unsupported package platform: {platform}")
            return None