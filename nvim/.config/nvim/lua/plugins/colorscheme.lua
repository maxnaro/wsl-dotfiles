return {
  {
    "qaptoR-nvim/chocolatier.nvim",
    lazy = false,
    priority = 1000,
    dependencies = { "rktjmp/lush.nvim" },
    config = function()
      local p = require("config.palette")
      local palette = { dark0 = p.bg, dark1 = p.surface, dark2 = p.selection, dark3 = p.selection,
        dark4 = p.muted, light0 = p.bright, light1 = p.fg }
      for name, color in pairs({ red = p.red, green = p.green, yellow = p.yellow, blue = p.blue,
        purple = p.purple, teal = p.cyan }) do
        for _, prefix in ipairs({ "light_", "neutral_", "bright_", "faded_" }) do
          palette[prefix .. name] = color
        end
      end
      require("chocolatier").setup({
        terminal_colors = false,
        palette_overrides = palette,
        transparent_mode = true,
        overrides = {
          WinSeparator = { fg = p.muted, bg = "NONE" },
          Pmenu = { fg = p.fg, bg = p.surface },
          PmenuSel = { fg = p.bright, bg = p.selection },
          -- Keep file states distinct and readable over selected and inactive rows.
          SnacksPickerPathHidden = { fg = p.picker.hidden },
          SnacksPickerPathIgnored = { fg = p.picker.muted },
          SnacksPickerDir = { fg = p.picker.muted },
          SnacksPickerDirectory = { fg = p.picker.blue, bold = true },
          SnacksPickerLink = { fg = p.picker.muted, italic = true },
          SnacksPickerLinkBroken = { fg = p.picker.red },
          SnacksPickerGitStatus = { fg = p.picker.yellow },
          SnacksPickerGitStatusAdded = { fg = p.picker.green },
          SnacksPickerGitStatusModified = { fg = p.picker.yellow },
          SnacksPickerGitStatusDeleted = { fg = p.picker.red },
          SnacksPickerGitStatusRenamed = { fg = p.picker.purple },
          SnacksPickerGitStatusCopied = { fg = p.picker.purple },
          SnacksPickerGitStatusUntracked = { fg = p.picker.blue },
          SnacksPickerGitStatusIgnored = { fg = p.picker.muted },
          SnacksPickerGitStatusUnmerged = { fg = p.picker.red },
          SnacksPickerGitStatusStaged = { fg = p.picker.cyan },
          BlinkCmpMenuBorder = { fg = p.cyan, bg = p.surface },
          BlinkCmpDocBorder = { fg = p.cyan, bg = "NONE" },
          BlinkCmpSignatureHelpBorder = { fg = p.cyan, bg = "NONE" },
          NoiceCmdlinePopupBorder = { fg = p.cyan, bg = "NONE" },
          StatusLine = { fg = "#D3C6AA", bg = "NONE" },
          StatusLineNC = { fg = "#907659", bg = "NONE" },
          FloatBorder = { fg = "#7EA69F", bg = "NONE" },
          LazyGitBorder = { fg = "#7EA69F", bg = "NONE" },
          LazyGitFloat = { fg = "#D3C6AA", bg = "NONE" },
        },
      })
      vim.cmd([[colorscheme chocolatier]])
      for index, color in ipairs(p.ansi) do
        vim.g["terminal_color_" .. index - 1] = color
      end
    end,
  },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "chocolatier",
    },
  },
}
