ARG VARIANT=ubuntu-22.04

FROM mcr.microsoft.com/vscode/devcontainers/base:0-${VARIANT}

# Install python
RUN sudo -E apt update && \
    sudo -E apt install -y software-properties-common && \
    sudo -E add-apt-repository -y ppa:deadsnakes/ppa && \
    sudo -E apt update && \
    sudo -E apt install -y python3.10 python3.10-venv python3.10-dev python3.10-distutils \
        python3.11 python3.11-venv python3.11-dev python3.11-distutils && \
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 10 && \
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 20