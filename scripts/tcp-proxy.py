#!/usr/bin/env python3
"""
Simple TCP port forwarder for GlueSync
Forwards 80->8080 and 443->8443
"""

import socket
import threading
import sys


def forward(source, destination):
    """Forward data between two sockets"""
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            destination.sendall(data)
    except:
        pass
    finally:
        source.close()
        destination.close()


def handle_client(client_socket, target_host, target_port):
    """Handle a single client connection"""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((target_host, target_port))
        
        # Start forwarding in both directions
        t1 = threading.Thread(target=forward, args=(client_socket, server_socket))
        t2 = threading.Thread(target=forward, args=(server_socket, client_socket))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(f"Error: {e}")
        client_socket.close()


def start_proxy(listen_port, target_host, target_port):
    """Start a TCP proxy"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', listen_port))
    server.listen(5)
    print(f"Proxy listening on port {listen_port} -> {target_host}:{target_port}")
    
    while True:
        client, addr = server.accept()
        print(f"Connection from {addr}")
        thread = threading.Thread(
            target=handle_client,
            args=(client, target_host, target_port)
        )
        thread.start()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='TCP Port Proxy')
    parser.add_argument('--listen', '-l', type=int, required=True, help='Listen port')
    parser.add_argument('--target-host', '-H', default='localhost', help='Target host')
    parser.add_argument('--target-port', '-p', type=int, required=True, help='Target port')
    args = parser.parse_args()
    
    start_proxy(args.listen, args.target_host, args.target_port)
