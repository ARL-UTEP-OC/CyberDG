echo "making log folder"
mkdir /shared/logs

sudo touch /shared/logs/pcaplog.pcapng
sudo DEBIAN_FRONTEND=noninteractive apt -y install tshark
sudo chmod 777 /shared/logs/pcaplog.pcapng
