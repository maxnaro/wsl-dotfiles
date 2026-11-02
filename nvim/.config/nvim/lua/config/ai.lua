local M = {}

function M.enabled()
  local client = package.loaded["copilot.client"]
  return client ~= nil and not client.is_disabled()
end

function M.set(enabled)
  if enabled then
    if not package.loaded["copilot"] then
      require("lazy").load({ plugins = { "copilot.lua" } })
    elseif not M.enabled() then
      require("copilot.command").enable()
    end
  elseif package.loaded["copilot"] then
    for _, buf in ipairs(vim.api.nvim_list_bufs()) do
      if vim.api.nvim_buf_is_loaded(buf) then
        vim.api.nvim_buf_call(buf, function()
          require("copilot.suggestion").dismiss()
          require("copilot.client").buf_detach_if_attached(buf)
        end)
      end
    end
    require("copilot.command").disable()
  end
end

function M.accept()
  local suggestion = package.loaded["copilot.suggestion"]
  if M.enabled() and suggestion and suggestion.is_visible() then
    suggestion.accept()
    return true
  end
end

function M.menu(open)
  vim.b.copilot_suggestion_hidden = open
  local suggestion = package.loaded["copilot.suggestion"]
  if suggestion and M.enabled() then
    if open then
      suggestion.clear_preview()
    else
      suggestion.update_preview()
    end
  end
end

return M
