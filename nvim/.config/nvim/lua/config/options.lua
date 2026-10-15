-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

-- Use OSC 52 clipboard for seamless copy/paste in WSL, Tmux, and SSH without external binaries
vim.g.clipboard = "osc52"
vim.opt.clipboard = "unnamedplus"
