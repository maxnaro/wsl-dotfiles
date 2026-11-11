"""Exercise a running Neovim instance against temporary theme state.

Run with python3 tests/live_theme.py after installing the Neovim plugins.
"""
import os,tempfile,subprocess,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
 t=pathlib.Path(tmp); c=t/'config'; s=t/'state'; (c/'dotfiles/theme').mkdir(parents=True); (s/'dotfiles/theme').mkdir(parents=True)
 (c/'dotfiles/theme/palette.json').write_text((root/'themes/chocolatier.json').read_text())
 (s/'dotfiles/theme/mode').write_text('dark\n')
 lua='''vim.opt.rtp:prepend("/home/max/dotfiles/nvim/.config/nvim")
vim.opt.rtp:prepend("/home/max/.local/share/nvim/lazy/chocolatier.nvim")
vim.opt.rtp:prepend("/home/max/.local/share/nvim/lazy/lush.nvim")
vim.opt.rtp:prepend("/home/max/.local/share/nvim/lazy/gruvbox")
vim.o.termguicolors = true
local spec = dofile("/home/max/dotfiles/nvim/.config/nvim/lua/plugins/colorscheme.lua")
spec[1].config()
assert(vim.o.background == "dark")
assert(require("config.palette").fg == "#D3AF86")
vim.fn.writefile({"light"}, vim.env.XDG_STATE_HOME .. "/dotfiles/theme/mode")
assert(vim.wait(1500, function() return vim.o.background == "light" end, 20), "watcher missed light")
assert(require("config.palette").fg == "#3C3836")
assert(vim.g.colors_name == "gruvbox")
assert(vim.g.gruvbox_contrast_light == "medium")
assert(vim.api.nvim_get_hl(0,{name="Comment",link=false}).fg == tonumber("928374",16))
assert(vim.api.nvim_get_hl(0,{name="GruvboxOrange",link=false}).fg == tonumber("AF3A03",16))
assert(vim.api.nvim_get_hl(0,{name="GruvboxPurple",link=false}).fg == tonumber("8F3F71",16))
assert(vim.api.nvim_get_hl(0,{name="Pmenu"}).bg == tonumber("EBDBB2",16))
local function transparent()
  for _, name in ipairs({"Normal", "NormalNC", "NormalFloat", "SignColumn", "FoldColumn", "StatusLine", "StatusLineNC", "FloatBorder", "WinSeparator", "LazyGitFloat", "GruvboxRedSign"}) do
    assert(vim.api.nvim_get_hl(0, {name=name, link=false}).bg == nil, name .. " lost transparency")
  end
end
transparent()
vim.cmd("colorscheme gruvbox")
transparent()
assert(vim.g.terminal_color_0 == "#FBF1C7")
spec[2].opts.colorscheme()
assert(vim.g.colors_name == "gruvbox", "LazyVim startup callback selected wrong scheme")
transparent()
vim.fn.writefile({"dark"}, vim.env.XDG_STATE_HOME .. "/dotfiles/theme/mode")
assert(vim.wait(1500, function() return vim.o.background == "dark" end,20), "watcher missed dark")
assert(vim.g.colors_name == "chocolatier")
assert(vim.api.nvim_get_hl(0,{name="Normal",link=false}).bg == nil)
assert(require("config.palette").fg == "#D3AF86")
vim.cmd("qa!")
'''
 lua = lua.replace("/home/max/dotfiles", str(root)).replace("/home/max/.local/share", str(pathlib.Path(os.environ.get("XDG_DATA_HOME", str(pathlib.Path.home()/".local/share")))))
 # Startup must also honour a saved light mode before any watcher event.
 startup = lua[:lua.index('assert(vim.o.background == "dark")')] + 'assert(vim.o.background == "light")\nassert(vim.g.colors_name == "gruvbox")\nassert(vim.g.gruvbox_contrast_light == "medium")\nassert(vim.api.nvim_get_hl(0, {name="Normal", link=false}).bg == nil)\nvim.cmd("qa!")\n'
 (s/'dotfiles/theme/mode').write_text('light\n')
 p=t/'startup.lua'; p.write_text(startup)
 result=subprocess.run(['nvim','--headless','-i','NONE','-u','NONE','-l',str(p)],env=dict(os.environ,XDG_CONFIG_HOME=str(c),XDG_STATE_HOME=str(s)),capture_output=True,text=True,timeout=8)
 assert result.returncode == 0, result.stdout + result.stderr
 (s/'dotfiles/theme/mode').write_text('dark\n')
 p=t/'test.lua';p.write_text(lua)
 result=subprocess.run(['nvim','--headless','-i','NONE','-u','NONE','-l',str(p)],env=dict(os.environ,XDG_CONFIG_HOME=str(c),XDG_STATE_HOME=str(s)),capture_output=True,text=True,timeout=8)
 print(result.stdout, result.stderr, end="")
 assert result.returncode==0
 print('Neovim theme watcher: dark -> light -> dark passed')
