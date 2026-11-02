-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

Snacks.toggle({
  name = "AI Autocomplete",
  get = function() return require("config.ai").enabled() end,
  set = function(enabled) require("config.ai").set(enabled) end,
}):map("<leader>au")
