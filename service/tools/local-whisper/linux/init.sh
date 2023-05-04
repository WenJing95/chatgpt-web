sudo apt update
sudo apt install build-essential -y

wget https://github.com/ggerganov/whisper.cpp/archive/refs/heads/master.zip
unzip master.zip
rm master.zip
cd whisper.cpp-master || exit

make

