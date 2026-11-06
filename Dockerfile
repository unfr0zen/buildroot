FROM debian:trixie-slim
RUN apt-get update && apt-get install -y --no-install-recommends build-essential bash bc binutils bzip2 ca-certificates cpio file git libncurses-dev patch perl python3 rsync unzip wget xz-utils && rm -rf /var/lib/apt/lists/*
RUN git config --system --add safe.directory /src && git config --system --add safe.directory /src/buildroot
ENV FORCE_UNSAFE_CONFIGURE=1
WORKDIR /src
