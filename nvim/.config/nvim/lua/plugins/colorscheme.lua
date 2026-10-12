return {
  {
    "qaptoR-nvim/chocolatier.nvim",
    lazy = false,
    priority = 1000,
    dependencies = { "rktjmp/lush.nvim" },
    config = function()
      -- Optional setup overrides can go here
      vim.cmd([[colorscheme chocolatier]])
    end,
  },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "chocolatier",
    },
  },
}
