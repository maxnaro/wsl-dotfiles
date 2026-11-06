return {
  {
    "saghen/blink.cmp",
    opts = function(_, opts)
      opts.keymap = opts.keymap or {}
      opts.keymap.preset = "super-tab"
      opts.keymap["<Tab>"] = {
        function(cmp)
          if cmp.is_menu_visible() then return cmp.select_and_accept() end
        end,
        "snippet_forward",
        function() return require("config.ai").accept() end,
        function(cmp)
          -- Reopen delayed or dismissed completions after a typed prefix.
          local before_cursor = vim.api.nvim_get_current_line():sub(1, vim.api.nvim_win_get_cursor(0)[2])
          if before_cursor:match("[%w_]$") then return cmp.show() end
        end,
        "fallback",
      }
      opts.keymap["<S-Tab>"] = { "select_prev", "snippet_backward", "fallback" }
    end,
  },
}
