return {
  {
    "nvim-lualine/lualine.nvim",
    opts = function(_, opts)
      local p = require("config.palette")
      local quiet = { fg = p.fg, bg = "NONE" }
      local theme = {}
      for _, mode in ipairs({ "normal", "insert", "visual", "replace", "command", "terminal", "inactive" }) do
        theme[mode] = { a = { fg = ({ insert = p.green, visual = p.purple, replace = p.red, command = p.yellow, terminal = p.blue, inactive = p.muted })[mode] or p.cyan, bg = "NONE" }, b = quiet, c = quiet }
      end
      opts.options.theme = theme
      opts.options.section_separators = ""
      opts.options.component_separators = ""
      opts.options.icons_enabled = false
      opts.sections = {
        lualine_a = { { "mode", fmt = function(mode) return mode:sub(1, 1) end } },
        lualine_b = { { "branch", color = { fg = p.purple } } },
        lualine_c = { { "filename", path = 1 } },
        lualine_x = {
          { function() return "REC @" .. vim.fn.reg_recording() end,
            cond = function() return vim.fn.reg_recording() ~= "" end, color = { fg = p.red } },
          { "diff", source = function()
            local status = vim.b.gitsigns_status_dict
            if status then
              return { added = status.added, modified = status.changed, removed = status.removed }
            end
          end },
          { "diagnostics", symbols = { error = "E:", warn = "W:", info = "I:", hint = "H:" } },
        },
        lualine_y = { "location" },
        lualine_z = {},
      }
    end,
  },
}
