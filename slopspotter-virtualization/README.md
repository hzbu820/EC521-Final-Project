# Virtual Machine Implementation

Setting up on your local machine only on first run:
    1. Download all the dependable packages
        a. sudo apt update
           sudo apt install -y \
           qemu-kvm \
           libvirt-daemon-system \
           libvirt-clients \
           virtinst \
           genisoimage \
           wget \
           python3-libvirt
    2. Add your user to the libvirt group
        a. sudo usermod -a -G libvirt $USER
    3. Install python packages
        a. pip install libvirt-python
    4. Install the Python package
    5.Run vm_image_builder_script.py
        a. Make the script an executable
            i. chmod +x vm_image_builder_script.py
        b. ./vm_image_builder_script.py --os ubuntu --size 20 --output-dir ./vm-images
    6. The code will 


Using the function in your code:
    1. Add the line - from qemu_sandbox import test_package_in_vm
    2. Use the function as so:
        a. result = test_package_in_vm(numpy, Python, path/to/vm.image)

        
