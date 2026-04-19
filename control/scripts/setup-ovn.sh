#!/bin/bash
# Initialize OVN for cloud platform

echo "Setting up OVN..."

# Create default public network
ovn-nbctl ls-add public-network

# Create default router
ovn-nbctl lr-add default-router

# Connect router to public network
ovn-nbctl lrp-add default-router lrp-public 02:00:00:00:00:01 192.168.100.1/24
ovn-nbctl lsp-add public-network lsp-public
ovn-nbctl lsp-set-type lsp-public router
ovn-nbctl lsp-set-addresses lsp-public router
ovn-nbctl lsp-set-options lsp-public router-port=lrp-public

# Create default private network
ovn-nbctl ls-add private-network

# Connect router to private network
ovn-nbctl lrp-add default-router lrp-private 02:00:00:00:00:02 10.0.0.1/24
ovn-nbctl lsp-add private-network lsp-private
ovn-nbctl lsp-set-type lsp-private router
ovn-nbctl lsp-set-addresses lsp-private router
ovn-nbctl lsp-set-options lsp-private router-port=lrp-private

echo "OVN setup complete!"
