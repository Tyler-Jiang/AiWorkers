import './style.css'

/** 占位页：真实玩法由 Cursor Cloud Agent / Developer 在本目录实现，勿写在控制台 frontend。 */
const app = document.querySelector<HTMLDivElement>('#app')!
app.innerHTML = `
  <main class="shell">
    <h1>产出区（独立项目）</h1>
    <p class="lead">
      此处为 <code>output/mini-game</code>，与 AI Game Studio 控制台（<code>frontend/</code>）分离。
    </p>
    <p>
      请通过 Cloud Agent 调用 Developer，在<strong>本目录</strong>编写点击类等小游戏；本地运行
      <code>npm run dev</code>（端口 <strong>5180</strong>）后，办公室可内嵌实时预览。
    </p>
  </main>
`
