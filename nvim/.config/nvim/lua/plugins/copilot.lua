return {
  {
    "zbirenbaum/copilot.lua",
    lazy = true,
    cmd = "Copilot",
    build = false,
    opts = {
      panel = { enabled = false },
      nes = { enabled = false },
      suggestion = {
        enabled = true,
        auto_trigger = true,
        trigger_on_accept = false,
        hide_during_completion = true,
        keymap = { accept = false, next = "<M-]>", prev = "<M-[>", dismiss = "<C-]>" },
      },
    },
    init = function()
      local group = vim.api.nvim_create_augroup("copilot_blink_menu", { clear = true })
      vim.api.nvim_create_autocmd("User", {
        group = group,
        pattern = { "BlinkCmpMenuOpen", "BlinkCmpMenuClose" },
        callback = function(event)
          require("config.ai").menu(event.match == "BlinkCmpMenuOpen")
        end,
      })
      vim.api.nvim_create_autocmd("BufEnter", {
        group = group,
        callback = function()
          local cmp = package.loaded["blink.cmp"]
          require("config.ai").menu(cmp ~= nil and cmp.is_menu_visible())
        end,
      })
    end,
  },
}
