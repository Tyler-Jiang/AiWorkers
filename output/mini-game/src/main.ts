import './style.css'

const DEMO_VERSION = 'Demo v0.1.0'
const SAVE_KEY = 'clicker-demo-save-v0-1-0'
const AUTO_SAVE_INTERVAL_MS = 60_000

const NUMERIC_CONFIG = {
  initialCoins: 0,
  baseClickValue: 1,
  baseUpgradeCost: 12,
  clickGrowth: 1.32,
  costGrowth: 1.58,
}

type SaveState = {
  version: string
  coins: number
  level: number
  clickValue: number
  guideDismissed: boolean
  savedAt: number
}

type GameState = Omit<SaveState, 'version'>

type PersistOptions = {
  showAutoSaveToast: boolean
}

const app = document.querySelector<HTMLDivElement>('#app')
if (!app) {
  throw new Error('页面缺少 #app 节点，无法启动游戏。')
}

app.innerHTML = `
  <main class="game-shell">
    <header class="header-card">
      <h1>点击成长小游戏</h1>
      <p class="subtitle">点击攒金币，升级强化每次点击收益</p>
      <p class="version">${DEMO_VERSION}</p>
    </header>

    <section class="coin-card">
      <p class="label">当前金币</p>
      <p class="coin-value" id="coinValue">0</p>
      <p class="income" id="incomeValue">每次点击 +1 金币</p>
    </section>

    <section class="action-card">
      <button id="clickBtn" class="primary-btn" type="button">点击赚金币</button>
    </section>

    <section class="upgrade-card">
      <h2>升级：强化点击</h2>
      <p>当前等级：<strong id="levelValue">0</strong></p>
      <p>下一级点击收益：<strong id="nextClickValue">2</strong></p>
      <p>升级花费：<strong id="costValue">12</strong> 金币</p>
      <button id="upgradeBtn" class="upgrade-btn" type="button">升级</button>
    </section>

    <section class="status-card">
      <button id="resetBtn" class="secondary-btn" type="button">重置存档</button>
      <span id="saveTip" class="save-tip" aria-live="polite"></span>
    </section>
  </main>

  <div id="guideMask" class="guide-mask" role="dialog" aria-modal="true" aria-labelledby="guideTitle">
    <div class="guide-card">
      <h2 id="guideTitle">新手引导</h2>
      <ol>
        <li>点击“点击赚金币”获取金币。</li>
        <li>金币足够后，点击“升级”提高每次点击收益。</li>
        <li>系统会自动保存，重开页面可继续进度。</li>
      </ol>
      <button id="guideCloseBtn" class="primary-btn" type="button">我知道了，开始游戏</button>
    </div>
  </div>
`

function getElement<T extends HTMLElement>(selector: string): T {
  const element = app.querySelector<T>(selector)
  if (!element) {
    throw new Error(`缺少必要节点：${selector}`)
  }
  return element
}

const coinValueEl = getElement<HTMLParagraphElement>('#coinValue')
const incomeValueEl = getElement<HTMLParagraphElement>('#incomeValue')
const levelValueEl = getElement<HTMLElement>('#levelValue')
const nextClickValueEl = getElement<HTMLElement>('#nextClickValue')
const costValueEl = getElement<HTMLElement>('#costValue')
const saveTipEl = getElement<HTMLSpanElement>('#saveTip')
const clickBtn = getElement<HTMLButtonElement>('#clickBtn')
const upgradeBtn = getElement<HTMLButtonElement>('#upgradeBtn')
const resetBtn = getElement<HTMLButtonElement>('#resetBtn')
const guideMask = getElement<HTMLDivElement>('#guideMask')
const guideCloseBtn = getElement<HTMLButtonElement>('#guideCloseBtn')

let tipTimer: number | undefined

function calculateClickValue(level: number): number {
  return Math.max(
    1,
    Math.floor(NUMERIC_CONFIG.baseClickValue * NUMERIC_CONFIG.clickGrowth ** level),
  )
}

function calculateUpgradeCost(level: number): number {
  return Math.max(
    1,
    Math.floor(NUMERIC_CONFIG.baseUpgradeCost * NUMERIC_CONFIG.costGrowth ** level),
  )
}

function sanitizeNumber(value: unknown, fallback: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback
  }
  return Math.max(0, Math.floor(value))
}

function createInitialState(): GameState {
  return {
    coins: NUMERIC_CONFIG.initialCoins,
    level: 0,
    clickValue: NUMERIC_CONFIG.baseClickValue,
    guideDismissed: false,
    savedAt: 0,
  }
}

function loadState(): GameState {
  const initialState = createInitialState()
  try {
    const raw = localStorage.getItem(SAVE_KEY)
    if (!raw) {
      return initialState
    }
    const parsed = JSON.parse(raw) as Partial<SaveState>
    const level = sanitizeNumber(parsed.level, initialState.level)
    const computedClickValue = calculateClickValue(level)
    const storedClickValue = sanitizeNumber(parsed.clickValue, computedClickValue)

    return {
      coins: sanitizeNumber(parsed.coins, initialState.coins),
      level,
      clickValue: Math.max(computedClickValue, storedClickValue),
      guideDismissed: Boolean(parsed.guideDismissed),
      savedAt: sanitizeNumber(parsed.savedAt, initialState.savedAt),
    }
  } catch (error) {
    console.error('读取存档失败，已回退默认进度。', error)
    return initialState
  }
}

function showTip(message: string): void {
  saveTipEl.textContent = message
  if (tipTimer) {
    window.clearTimeout(tipTimer)
  }
  tipTimer = window.setTimeout(() => {
    saveTipEl.textContent = ''
  }, 1800)
}

function persistState(state: GameState, options: PersistOptions): void {
  const payload: SaveState = {
    version: DEMO_VERSION,
    coins: state.coins,
    level: state.level,
    clickValue: state.clickValue,
    guideDismissed: state.guideDismissed,
    savedAt: Date.now(),
  }

  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify(payload))
    state.savedAt = payload.savedAt
    if (options.showAutoSaveToast) {
      showTip('已自动保存')
    }
  } catch (error) {
    console.error('保存失败，浏览器可能禁用了本地存储。', error)
    showTip('保存失败：请检查浏览器存储权限')
  }
}

function formatNumber(value: number): string {
  const safeValue = Math.max(0, Math.floor(value))
  if (safeValue >= 1_000_000) {
    return `${Math.floor(safeValue / 1_000_000)}M`
  }
  if (safeValue >= 1_000) {
    return `${Math.floor(safeValue / 1_000)}K`
  }
  return `${safeValue}`
}

let gameState = loadState()

function render(): void {
  const cost = calculateUpgradeCost(gameState.level)
  const nextClickValue = calculateClickValue(gameState.level + 1)
  const canUpgrade = gameState.coins >= cost

  coinValueEl.textContent = `${formatNumber(gameState.coins)} 金币`
  incomeValueEl.textContent = `每次点击 +${formatNumber(gameState.clickValue)} 金币`
  levelValueEl.textContent = formatNumber(gameState.level)
  nextClickValueEl.textContent = `${formatNumber(nextClickValue)} 金币`
  costValueEl.textContent = formatNumber(cost)
  upgradeBtn.disabled = !canUpgrade
  upgradeBtn.textContent = canUpgrade
    ? `升级（花费 ${formatNumber(cost)}）`
    : `金币不足（需要 ${formatNumber(cost)}）`
}

function showGuideIfNeeded(): void {
  if (gameState.guideDismissed) {
    guideMask.classList.add('hidden')
    return
  }
  guideMask.classList.remove('hidden')
}

clickBtn.addEventListener('click', () => {
  gameState.coins += gameState.clickValue
  render()
})

upgradeBtn.addEventListener('click', () => {
  const cost = calculateUpgradeCost(gameState.level)
  if (gameState.coins < cost) {
    return
  }
  gameState.coins -= cost
  gameState.level += 1
  gameState.clickValue = calculateClickValue(gameState.level)
  render()
  persistState(gameState, { showAutoSaveToast: true })
})

guideCloseBtn.addEventListener('click', () => {
  gameState.guideDismissed = true
  guideMask.classList.add('hidden')
  persistState(gameState, { showAutoSaveToast: false })
})

resetBtn.addEventListener('click', () => {
  const firstConfirm = window.confirm('确定要重置存档吗？当前进度将清空。')
  if (!firstConfirm) {
    return
  }
  const secondConfirm = window.confirm('请再次确认：重置后无法恢复，是否继续？')
  if (!secondConfirm) {
    return
  }

  localStorage.removeItem(SAVE_KEY)
  gameState = createInitialState()
  render()
  showGuideIfNeeded()
  showTip('存档已重置')
})

window.setInterval(() => {
  persistState(gameState, { showAutoSaveToast: true })
}, AUTO_SAVE_INTERVAL_MS)

render()
showGuideIfNeeded()
