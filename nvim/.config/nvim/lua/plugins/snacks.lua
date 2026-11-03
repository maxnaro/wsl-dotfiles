local header = [[
██╗   ██╗██╗███╗   ███╗                         Z
██║   ██║╚═╝████╗ ████║                     Z
██║   ██║██╗██╔████╔██║ ██████╗██╗ ██╗  z
╚██╗ ██╔╝██║██║╚██╔╝██║██╔══██║╚████╔╝
 ╚████╔╝ ██║██║ ╚═╝ ██║╚██████║██╔═██╗
  ╚═══╝  ╚═╝╚═╝     ╚═╝ ╚═════╝╚═╝ ╚═╝
]]

-- Snacks centers each line separately, so preserve the artwork's shared width.
local header_lines = vim.split(header, "\n", { trimempty = true })
local header_width = 0
for _, line in ipairs(header_lines) do
  header_width = math.max(header_width, vim.fn.strdisplaywidth(line))
end
for i, line in ipairs(header_lines) do
  header_lines[i] = line .. string.rep(" ", header_width - vim.fn.strdisplaywidth(line))
end

return {
  {
    "folke/snacks.nvim",
    opts = {
      dashboard = {
        preset = {
          header = table.concat(header_lines, "\n"),
        },
      },
      picker = {
        sources = {
          files = { hidden = true },
          explorer = { hidden = true },
        },
      },
    },
  },
}
