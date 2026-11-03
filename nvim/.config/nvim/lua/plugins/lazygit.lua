return {
  {
    "folke/snacks.nvim",
    opts = function(_, opts)
      local p = require("config.palette")
      opts.lazygit = vim.tbl_deep_extend("force", opts.lazygit or {}, {
        config = { gui = { theme = {
          activeBorderColor = { p.cyan, "bold" }, inactiveBorderColor = { p.muted },
          searchingActiveBorderColor = { p.purple, "bold" }, defaultFgColor = { p.fg },
          optionsTextColor = { p.cyan }, selectedLineBgColor = { "default" },
        } } },
        win = { border = "rounded", backdrop = false },
      })
    end,
  },
}
