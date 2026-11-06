-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

vim.g.ai_cmp = false

-- Keep search and explorer rooted at the Git repository before LSP workspaces.
vim.g.root_spec = { ".git", "lsp", "cwd" }
