# Buffett Letter Reader — 开发 Prompt

## 项目目标

基于 Vite 构建一个静态 HTML 页面，用于精读巴菲特致股东信。页面左右分栏：左边是英文原文，右边是对应的中文精读解析。

## 已有文件

项目已经搭好了 Vite 脚手架（`site/` 目录），以下文件已写好可直接使用：

- `site/index.html` — 入口 HTML
- `site/src/main.js` — 渲染逻辑（读取数据，渲染分栏页面，支持目录跳转）
- `site/src/style.css` — 完整样式（双栏布局、sticky 导航、标签、响应式）

**唯一需要生成的是数据文件 `site/src/data/1983.js`。**

## 数据结构

`1983.js` 导出一个 `letter1983` 对象，结构如下：

```js
export const letter1983 = {
  year: 1983,
  title: "Berkshire Hathaway 1983 致股东信 · 精读",
  subtitle: "13 条商业原则 · NFM 收购 · 账面价值 vs 内在价值 · 经济商誉",
  sections: [
    {
      id: "principles",
      title: "13 条商业原则",
      pairs: [
        {
          tags: [
            { type: "term", label: "术语" },
            { type: "quote", label: "金句" },
            // type 可选: term(术语), quote(金句), context(背景), logic(逻辑链), crossref(跨信关联)
          ],
          original: "原文段落（英文 HTML）",
          notes: "中文解析（HTML，可包含 <p>, <blockquote>, <table> 等）"
        },
        // ... 更多 pairs
      ]
    },
    // ... 更多 sections
  ]
}
```

## 原文来源

完整原文在 `letters/1983.md`，请从中提取原文段落。

## 解析风格

对照我们已有的精读笔记 `notes/1983-精读笔记.md`，按以下标准为每一段原文撰写右栏解析：

1. **逐句翻译**：忠实流畅的中文翻译，不跳过关键句
2. **术语拆解**：遇到专业术语给中英对照和通俗解释（如 intrinsic value = 内在价值 = 未来现金流折现值）
3. **背景补充**：巴菲特提到的人物、事件、公司的上下文（如"老师"指格雷厄姆，Mrs. B 的生平）
4. **投资逻辑链**：把隐含推理显式化（如"低费用率 → 让利客户 → 销量大 → 总利润更高"）
5. **跨信件关联**：与其他年份信件的呼应（如经济商誉 → 2007 年护城河论述）
6. **金句标注**：值得反复品味的原文用 `<blockquote>` 高亮
7. **保留巴菲特的幽默和修辞**：翻译时保留节奏感，点明讽刺、自嘲、类比的妙处

## sections 拆分

按以下章节拆分，每个章节内按自然段落做 pairs：

1. `principles` — 13 条商业原则（每条原则一个 pair 或相关的合并为一个）
2. `nfm` — Nebraska Furniture Mart 收购故事
3. `performance` — Corporate Performance（账面价值 vs 内在价值、经济商誉）
4. `earnings` — 盈利来源与投资组合（财务数据表可作为一个 pair，解析关键数字）
5. `buffalo` — Buffalo News
6. `sees` — See's Candies
7. `insurance` — 保险业务（自营 + GEICO）
8. `stock-split` — 为什么不拆股 + 对频繁交易的批判
9. `goodwill-appendix` — 商誉附录（经济商誉 vs 会计商誉，用 See's Candies 做案例）

## 注意事项

- `original` 和 `notes` 字段都是 **HTML 字符串**，不是 Markdown
- 原文中的引号、撇号等特殊字符已修复（cp1252 → UTF-8），直接使用即可
- 不需要太碎——相关的短段落可以合并为一个 pair，一般 3-8 句为一个 pair
- 每个 pair 的 tags 选 1-2 个最相关的即可，不用全部都加
- 表格数据可以简化，只保留最关键的数字和分析
