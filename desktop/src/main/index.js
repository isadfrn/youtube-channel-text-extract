import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron'
import { join } from 'path'
import { spawn, execSync } from 'child_process'
import { homedir } from 'os'

// ── ANSI stripping ─────────────────────────────────────────────────────────────

const ANSI_RE = /\x1b\[[0-9;]*[mGKHF]/g
const stripAnsi = (s) => s.replace(ANSI_RE, '')

// ── State ──────────────────────────────────────────────────────────────────────

let mainWindow = null
let activeProcess = null

// ── Window ─────────────────────────────────────────────────────────────────────

function createWindow() {
  const iconPath = join(app.getAppPath(), 'build', 'icon.ico')

  mainWindow = new BrowserWindow({
    width: 780,
    height: 760,
    minWidth: 680,
    minHeight: 580,
    icon: iconPath,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (activeProcess) killProcess(activeProcess)
  if (process.platform !== 'darwin') app.quit()
})

// ── Process helpers ────────────────────────────────────────────────────────────

function killProcess(proc) {
  if (!proc) return
  try {
    if (process.platform === 'win32' && proc.pid) {
      // Kill entire process tree (catches yt-dlp's FFmpeg child)
      execSync(`taskkill /F /T /PID ${proc.pid}`, { stdio: 'ignore' })
    } else {
      proc.kill('SIGTERM')
    }
  } catch {
    // Process may have already exited
  }
}

function commandExists(cmd) {
  try {
    const checker = process.platform === 'win32' ? 'where' : 'which'
    execSync(`${checker} ${cmd}`, { stdio: 'ignore' })
    return true
  } catch {
    return false
  }
}

/**
 * Parent directory that contains the ytextract/ Python package.
 *
 * Dev mode   → <project_root>/src/   (src/ytextract/ is the package)
 * Packaged   → process.resourcesPath  (extraResources copies it to resources/ytextract/)
 */
function getPythonSrcParent() {
  return app.isPackaged
    ? process.resourcesPath
    : join(app.getAppPath(), '..', 'src')
}

function findPython() {
  const candidates =
    process.platform === 'win32'
      ? ['python', 'python3', 'py']
      : ['python3', 'python']
  return candidates.find(commandExists) ?? null
}

/**
 * Resolve the best way to run the ytextract CLI.
 * Priority: installed `ytextract` command → python3/python -m ytextract.cli
 */
function resolveSpawnConfig(cliArgs) {
  // Option 1: ytextract installed via pip
  if (commandExists('ytextract')) {
    return {
      cmd: 'ytextract',
      args: cliArgs,
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
      shell: process.platform === 'win32', // .cmd wrapper on Windows needs shell
    }
  }

  // Option 2: Run as Python module with PYTHONPATH set to the parent of ytextract/
  const srcParent = getPythonSrcParent()
  const sep = process.platform === 'win32' ? ';' : ':'
  const PYTHONPATH = process.env.PYTHONPATH
    ? `${srcParent}${sep}${process.env.PYTHONPATH}`
    : srcParent

  const python = findPython()
  const cmd = python ?? (process.platform === 'win32' ? 'python' : 'python3')

  return {
    cmd,
    args: ['-m', 'ytextract.cli', ...cliArgs],
    env: { ...process.env, PYTHONPATH, PYTHONUNBUFFERED: '1' },
    shell: false,
  }
}

// ── Setup check ────────────────────────────────────────────────────────────────

ipcMain.handle('check-setup', () => {
  return {
    python: !!findPython(),
    ffmpeg: commandExists('ffmpeg'),
  }
})

function buildCliArgs(options) {
  const { channelUrl, outputDir, format, model, noArchive, force, withTimestamps } = options
  const args = [channelUrl]
  if (outputDir) args.push('-o', outputDir)
  args.push('-f', format, '-m', model)
  if (noArchive) args.push('--no-archive')
  if (force) args.push('--force')
  if (withTimestamps) args.push('--with-timestamps')
  return args
}

// ── IPC handlers ───────────────────────────────────────────────────────────────

ipcMain.handle('get-desktop-path', () => join(homedir(), 'Desktop'))

ipcMain.handle('select-directory', async (_, defaultPath) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    defaultPath: defaultPath || join(homedir(), 'Desktop'),
  })
  return result.canceled ? null : result.filePaths[0]
})

ipcMain.handle('open-folder', async (_, folderPath) => {
  await shell.openPath(folderPath)
})

ipcMain.on('start-extraction', (event, options) => {
  if (activeProcess) return

  const cliArgs = buildCliArgs(options)
  const { cmd, args, env, shell: useShell } = resolveSpawnConfig(cliArgs)

  let proc
  try {
    proc = spawn(cmd, args, { env, shell: useShell })
  } catch (err) {
    event.sender.send('extract:log', `Failed to start process: ${err.message}`)
    event.sender.send('extract:done', 1)
    return
  }

  activeProcess = proc

  // Line-buffered stream handler
  let buffer = ''
  function processData(chunk) {
    buffer += chunk.toString()
    const lines = buffer.split('\n')
    buffer = lines.pop() // keep incomplete last line
    for (const line of lines) {
      // \r within a line = yt-dlp progress overwrite; keep only the last segment
      const clean = stripAnsi(line.split('\r').pop() ?? line).trimEnd()
      if (clean) event.sender.send('extract:log', clean)
    }
  }

  proc.stdout.on('data', processData)
  proc.stderr.on('data', processData)

  proc.on('close', (code) => {
    // Flush any remaining buffered text
    const remaining = stripAnsi(buffer).trimEnd()
    if (remaining) event.sender.send('extract:log', remaining)
    event.sender.send('extract:done', code ?? 1)
    activeProcess = null
  })

  proc.on('error', (err) => {
    const isNotFound = err.code === 'ENOENT'
    const msg = isNotFound
      ? `Command not found: "${cmd}".\nMake sure Python is installed and ytextract is set up:\n  pip install -e .`
      : `Process error: ${err.message}`
    event.sender.send('extract:log', msg)
    event.sender.send('extract:done', 1)
    activeProcess = null
  })
})

ipcMain.on('stop-extraction', () => {
  if (activeProcess) {
    killProcess(activeProcess)
    activeProcess = null
  }
})
