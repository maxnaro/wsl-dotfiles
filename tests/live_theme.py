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
local spec = dofile("/home/max/dotfiles/nvim/.config/nvim/lua/plugins/colorscheme.lua")
spec[1].config()
assert(vim.o.background == "dark")
assert(require("config.palette").fg == "#D3C6AA")
vim.fn.writefile({"light"}, vim.env.XDG_STATE_HOME .. "/dotfiles/theme/mode")
assert(vim.wait(1500, function() return vim.o.background == "light" end, 20), "watcher missed light")
assert(require("config.palette").fg == "#625348")
assert(vim.api.nvim_get_hl(0,{name="Comment",link=false}).fg == tonumber(require("config.palette").picker.muted:sub(2),16))
assert(vim.api.nvim_get_hl(0,{name="ChocolatierOrange",link=false}).fg == tonumber("916D36",16))
assert(vim.api.nvim_get_hl(0,{name="ChocolatierFuscia",link=false}).fg == tonumber("8B6988",16))
assert(vim.api.nvim_get_hl(0,{name="Pmenu"}).bg == tonumber("E6DAC8",16))
vim.fn.writefile({"dark"}, vim.env.XDG_STATE_HOME .. "/dotfiles/theme/mode")
assert(vim.wait(1500, function() return vim.o.background == "dark" end,20), "watcher missed dark")
vim.cmd("qa!")
'''
 lua = lua.replace("/home/max/dotfiles", str(root)).replace("/home/max/.local/share", str(pathlib.Path(os.environ.get("XDG_DATA_HOME", str(pathlib.Path.home()/".local/share")))))
 p=t/'test.lua';p.write_text(lua)
 result=subprocess.run(['nvim','--headless','-i','NONE','-u','NONE','-l',str(p)],env=dict(os.environ,XDG_CONFIG_HOME=str(c),XDG_STATE_HOME=str(s)),capture_output=True,text=True,timeout=8)
 print(result.stdout, result.stderr, end="")
 assert result.returncode==0
 print('Neovim theme watcher: dark -> light -> dark passed')
