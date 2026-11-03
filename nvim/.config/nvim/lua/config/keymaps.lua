-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

Snacks.toggle({
  name = "AI Autocomplete",
  get = function() return require("config.ai").enabled() end,
  set = function(enabled) require("config.ai").set(enabled) end,
}):map("<leader>au")

vim.keymap.del("n", "<leader>l")
vim.keymap.set("n", "<leader>lz", "<cmd>Lazy<cr>", { desc = "Plugin Manager" })
vim.keymap.set("n", "<leader>lg", function()
  Snacks.lazygit({ cwd = LazyVim.root.git() })
end, { desc = "LazyGit (Root Dir)" })
