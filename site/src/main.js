import './style.css'
import { letter1983 } from './data/1983.js'

const letters = { 1983: letter1983 }

function renderTag(t) {
  return `<span class="tag tag-${t.type}">${t.label}</span>`
}

function renderPair(pair) {
  const tags = (pair.tags || []).map(renderTag).join('')
  return `
    <div class="pair">
      <div class="col-original">${pair.original}</div>
      <div class="col-notes">
        ${tags ? `<div class="tags">${tags}</div>` : ''}
        ${pair.notes}
      </div>
    </div>`
}

function renderSection(section) {
  return `
    <div class="section" id="section-${section.id}">
      <h2 class="section-title">${section.title}</h2>
      ${section.pairs.map(renderPair).join('')}
    </div>`
}

function renderToc(letter) {
  const opts = letter.sections
    .map(s => `<option value="section-${s.id}">${s.title}</option>`)
    .join('')
  return `<select onchange="if(this.value){document.getElementById(this.value).scrollIntoView({behavior:'smooth'});this.selectedIndex=0}">
    <option value="">跳转到...</option>${opts}</select>`
}

function render(letter) {
  document.getElementById('app').innerHTML = `
    <nav class="nav">
      <div class="nav-title">巴菲特致股东信 · 精读</div>
      <div class="nav-year">${letter.year}</div>
      <div class="nav-toc">${renderToc(letter)}</div>
    </nav>
    <div class="container">
      <h1 class="page-title">${letter.title}</h1>
      <p class="page-subtitle">${letter.subtitle}</p>
      ${letter.sections.map(renderSection).join('')}
    </div>`
}

render(letters[1983])
