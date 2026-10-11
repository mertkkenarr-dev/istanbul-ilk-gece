import{n as e,r as t,t as n}from"./dil-CNTITPEl.js";function r(){return{async:!1,breaks:!1,extensions:null,gfm:!0,hooks:null,pedantic:!1,renderer:null,silent:!1,tokenizer:null,walkTokens:null}}var i=r();function a(e){i=e}var o=/[&<>"']/,s=new RegExp(o.source,`g`),c=/[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/,l=new RegExp(c.source,`g`),u={"&":`&amp;`,"<":`&lt;`,">":`&gt;`,'"':`&quot;`,"'":`&#39;`},d=e=>u[e];function f(e,t){if(t){if(o.test(e))return e.replace(s,d)}else if(c.test(e))return e.replace(l,d);return e}var p=/&(#(?:\d+)|(?:#x[0-9A-Fa-f]+)|(?:\w+));?/gi;function ee(e){return e.replace(p,(e,t)=>(t=t.toLowerCase(),t===`colon`?`:`:t.charAt(0)===`#`?t.charAt(1)===`x`?String.fromCharCode(parseInt(t.substring(2),16)):String.fromCharCode(+t.substring(1)):``))}var te=/(^|[^\[])\^/g;function m(e,t){let n=typeof e==`string`?e:e.source;t||=``;let r={replace:(e,t)=>{let i=typeof t==`string`?t:t.source;return i=i.replace(te,`$1`),n=n.replace(e,i),r},getRegex:()=>new RegExp(n,t)};return r}function h(e){try{e=encodeURI(e).replace(/%25/g,`%`)}catch{return null}return e}var g={exec:()=>null};function _(e,t){let n=e.replace(/\|/g,(e,t,n)=>{let r=!1,i=t;for(;--i>=0&&n[i]===`\\`;)r=!r;return r?`|`:` |`}).split(/ \|/),r=0;if(n[0].trim()||n.shift(),n.length>0&&!n[n.length-1].trim()&&n.pop(),t){if(n.length>t)n.splice(t);else for(;n.length<t;)n.push(``)}for(;r<n.length;r++)n[r]=n[r].trim().replace(/\\\|/g,`|`);return n}function v(e,t,n){let r=e.length;if(r===0)return``;let i=0;for(;i<r;){let a=e.charAt(r-i-1);if(a===t&&!n)i++;else if(a!==t&&n)i++;else break}return e.slice(0,r-i)}function ne(e,t){if(e.indexOf(t[1])===-1)return-1;let n=0;for(let r=0;r<e.length;r++)if(e[r]===`\\`)r++;else if(e[r]===t[0])n++;else if(e[r]===t[1]&&(n--,n<0))return r;return-1}function y(e,t,n,r){let i=t.href,a=t.title?f(t.title):null,o=e[1].replace(/\\([\[\]])/g,`$1`);if(e[0].charAt(0)!==`!`){r.state.inLink=!0;let e={type:`link`,raw:n,href:i,title:a,text:o,tokens:r.inlineTokens(o)};return r.state.inLink=!1,e}return{type:`image`,raw:n,href:i,title:a,text:f(o)}}function re(e,t){let n=e.match(/^(\s+)(?:```)/);if(n===null)return t;let r=n[1];return t.split(`
`).map(e=>{let t=e.match(/^\s+/);if(t===null)return e;let[n]=t;return n.length>=r.length?e.slice(r.length):e}).join(`
`)}var b=class{options;rules;lexer;constructor(e){this.options=e||i}space(e){let t=this.rules.block.newline.exec(e);if(t&&t[0].length>0)return{type:`space`,raw:t[0]}}code(e){let t=this.rules.block.code.exec(e);if(t){let e=t[0].replace(/^ {1,4}/gm,``);return{type:`code`,raw:t[0],codeBlockStyle:`indented`,text:this.options.pedantic?e:v(e,`
`)}}}fences(e){let t=this.rules.block.fences.exec(e);if(t){let e=t[0],n=re(e,t[3]||``);return{type:`code`,raw:e,lang:t[2]?t[2].trim().replace(this.rules.inline.anyPunctuation,`$1`):t[2],text:n}}}heading(e){let t=this.rules.block.heading.exec(e);if(t){let e=t[2].trim();if(/#$/.test(e)){let t=v(e,`#`);(this.options.pedantic||!t||/ $/.test(t))&&(e=t.trim())}return{type:`heading`,raw:t[0],depth:t[1].length,text:e,tokens:this.lexer.inline(e)}}}hr(e){let t=this.rules.block.hr.exec(e);if(t)return{type:`hr`,raw:t[0]}}blockquote(e){let t=this.rules.block.blockquote.exec(e);if(t){let e=t[0].replace(/\n {0,3}((?:=+|-+) *)(?=\n|$)/g,`
    $1`);e=v(e.replace(/^ *>[ \t]?/gm,``),`
`);let n=this.lexer.state.top;this.lexer.state.top=!0;let r=this.lexer.blockTokens(e);return this.lexer.state.top=n,{type:`blockquote`,raw:t[0],tokens:r,text:e}}}list(e){let t=this.rules.block.list.exec(e);if(t){let n=t[1].trim(),r=n.length>1,i={type:`list`,raw:``,ordered:r,start:r?+n.slice(0,-1):``,loose:!1,items:[]};n=r?`\\d{1,9}\\${n.slice(-1)}`:`\\${n}`,this.options.pedantic&&(n=r?n:`[*+-]`);let a=RegExp(`^( {0,3}${n})((?:[\t ][^\\n]*)?(?:\\n|$))`),o=``,s=``,c=!1;for(;e;){let n=!1;if(!(t=a.exec(e))||this.rules.block.hr.test(e))break;o=t[0],e=e.substring(o.length);let r=t[2].split(`
`,1)[0].replace(/^\t+/,e=>` `.repeat(3*e.length)),l=e.split(`
`,1)[0],u=0;this.options.pedantic?(u=2,s=r.trimStart()):(u=t[2].search(/[^ ]/),u=u>4?1:u,s=r.slice(u),u+=t[1].length);let d=!1;if(!r&&/^ *$/.test(l)&&(o+=l+`
`,e=e.substring(l.length+1),n=!0),!n){let t=RegExp(`^ {0,${Math.min(3,u-1)}}(?:[*+-]|\\d{1,9}[.)])((?:[ \t][^\\n]*)?(?:\\n|$))`),n=RegExp(`^ {0,${Math.min(3,u-1)}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`),i=RegExp(`^ {0,${Math.min(3,u-1)}}(?:\`\`\`|~~~)`),a=RegExp(`^ {0,${Math.min(3,u-1)}}#`);for(;e;){let c=e.split(`
`,1)[0];if(l=c,this.options.pedantic&&(l=l.replace(/^ {1,4}(?=( {4})*[^ ])/g,`  `)),i.test(l)||a.test(l)||t.test(l)||n.test(e))break;if(l.search(/[^ ]/)>=u||!l.trim())s+=`
`+l.slice(u);else{if(d||r.search(/[^ ]/)>=4||i.test(r)||a.test(r)||n.test(r))break;s+=`
`+l}!d&&!l.trim()&&(d=!0),o+=c+`
`,e=e.substring(c.length+1),r=l.slice(u)}}i.loose||(c?i.loose=!0:/\n *\n *$/.test(o)&&(c=!0));let f=null,p;this.options.gfm&&(f=/^\[[ xX]\] /.exec(s),f&&(p=f[0]!==`[ ] `,s=s.replace(/^\[[ xX]\] +/,``))),i.items.push({type:`list_item`,raw:o,task:!!f,checked:p,loose:!1,text:s,tokens:[]}),i.raw+=o}i.items[i.items.length-1].raw=o.trimEnd(),i.items[i.items.length-1].text=s.trimEnd(),i.raw=i.raw.trimEnd();for(let e=0;e<i.items.length;e++)if(this.lexer.state.top=!1,i.items[e].tokens=this.lexer.blockTokens(i.items[e].text,[]),!i.loose){let t=i.items[e].tokens.filter(e=>e.type===`space`);i.loose=t.length>0&&t.some(e=>/\n.*\n/.test(e.raw))}if(i.loose)for(let e=0;e<i.items.length;e++)i.items[e].loose=!0;return i}}html(e){let t=this.rules.block.html.exec(e);if(t)return{type:`html`,block:!0,raw:t[0],pre:t[1]===`pre`||t[1]===`script`||t[1]===`style`,text:t[0]}}def(e){let t=this.rules.block.def.exec(e);if(t){let e=t[1].toLowerCase().replace(/\s+/g,` `),n=t[2]?t[2].replace(/^<(.*)>$/,`$1`).replace(this.rules.inline.anyPunctuation,`$1`):``,r=t[3]?t[3].substring(1,t[3].length-1).replace(this.rules.inline.anyPunctuation,`$1`):t[3];return{type:`def`,tag:e,raw:t[0],href:n,title:r}}}table(e){let t=this.rules.block.table.exec(e);if(!t||!/[:|]/.test(t[2]))return;let n=_(t[1]),r=t[2].replace(/^\||\| *$/g,``).split(`|`),i=t[3]&&t[3].trim()?t[3].replace(/\n[ \t]*$/,``).split(`
`):[],a={type:`table`,raw:t[0],header:[],align:[],rows:[]};if(n.length===r.length){for(let e of r)/^ *-+: *$/.test(e)?a.align.push(`right`):/^ *:-+: *$/.test(e)?a.align.push(`center`):/^ *:-+ *$/.test(e)?a.align.push(`left`):a.align.push(null);for(let e of n)a.header.push({text:e,tokens:this.lexer.inline(e)});for(let e of i)a.rows.push(_(e,a.header.length).map(e=>({text:e,tokens:this.lexer.inline(e)})));return a}}lheading(e){let t=this.rules.block.lheading.exec(e);if(t)return{type:`heading`,raw:t[0],depth:t[2].charAt(0)===`=`?1:2,text:t[1],tokens:this.lexer.inline(t[1])}}paragraph(e){let t=this.rules.block.paragraph.exec(e);if(t){let e=t[1].charAt(t[1].length-1)===`
`?t[1].slice(0,-1):t[1];return{type:`paragraph`,raw:t[0],text:e,tokens:this.lexer.inline(e)}}}text(e){let t=this.rules.block.text.exec(e);if(t)return{type:`text`,raw:t[0],text:t[0],tokens:this.lexer.inline(t[0])}}escape(e){let t=this.rules.inline.escape.exec(e);if(t)return{type:`escape`,raw:t[0],text:f(t[1])}}tag(e){let t=this.rules.inline.tag.exec(e);if(t)return!this.lexer.state.inLink&&/^<a /i.test(t[0])?this.lexer.state.inLink=!0:this.lexer.state.inLink&&/^<\/a>/i.test(t[0])&&(this.lexer.state.inLink=!1),!this.lexer.state.inRawBlock&&/^<(pre|code|kbd|script)(\s|>)/i.test(t[0])?this.lexer.state.inRawBlock=!0:this.lexer.state.inRawBlock&&/^<\/(pre|code|kbd|script)(\s|>)/i.test(t[0])&&(this.lexer.state.inRawBlock=!1),{type:`html`,raw:t[0],inLink:this.lexer.state.inLink,inRawBlock:this.lexer.state.inRawBlock,block:!1,text:t[0]}}link(e){let t=this.rules.inline.link.exec(e);if(t){let e=t[2].trim();if(!this.options.pedantic&&/^</.test(e)){if(!/>$/.test(e))return;let t=v(e.slice(0,-1),`\\`);if((e.length-t.length)%2==0)return}else{let e=ne(t[2],`()`);if(e>-1){let n=(t[0].indexOf(`!`)===0?5:4)+t[1].length+e;t[2]=t[2].substring(0,e),t[0]=t[0].substring(0,n).trim(),t[3]=``}}let n=t[2],r=``;if(this.options.pedantic){let e=/^([^'"]*[^\s])\s+(['"])(.*)\2/.exec(n);e&&(n=e[1],r=e[3])}else r=t[3]?t[3].slice(1,-1):``;return n=n.trim(),/^</.test(n)&&(n=this.options.pedantic&&!/>$/.test(e)?n.slice(1):n.slice(1,-1)),y(t,{href:n&&n.replace(this.rules.inline.anyPunctuation,`$1`),title:r&&r.replace(this.rules.inline.anyPunctuation,`$1`)},t[0],this.lexer)}}reflink(e,t){let n;if((n=this.rules.inline.reflink.exec(e))||(n=this.rules.inline.nolink.exec(e))){let e=t[(n[2]||n[1]).replace(/\s+/g,` `).toLowerCase()];if(!e){let e=n[0].charAt(0);return{type:`text`,raw:e,text:e}}return y(n,e,n[0],this.lexer)}}emStrong(e,t,n=``){let r=this.rules.inline.emStrongLDelim.exec(e);if(r&&!(r[3]&&n.match(/[\p{L}\p{N}]/u))&&(!(r[1]||r[2])||!n||this.rules.inline.punctuation.exec(n))){let n=[...r[0]].length-1,i,a,o=n,s=0,c=r[0][0]===`*`?this.rules.inline.emStrongRDelimAst:this.rules.inline.emStrongRDelimUnd;for(c.lastIndex=0,t=t.slice(-1*e.length+n);(r=c.exec(t))!=null;){if(i=r[1]||r[2]||r[3]||r[4]||r[5]||r[6],!i)continue;if(a=[...i].length,r[3]||r[4]){o+=a;continue}if((r[5]||r[6])&&n%3&&!((n+a)%3)){s+=a;continue}if(o-=a,o>0)continue;a=Math.min(a,a+o+s);let t=[...r[0]][0].length,c=e.slice(0,n+r.index+t+a);if(Math.min(n,a)%2){let e=c.slice(1,-1);return{type:`em`,raw:c,text:e,tokens:this.lexer.inlineTokens(e)}}let l=c.slice(2,-2);return{type:`strong`,raw:c,text:l,tokens:this.lexer.inlineTokens(l)}}}}codespan(e){let t=this.rules.inline.code.exec(e);if(t){let e=t[2].replace(/\n/g,` `),n=/[^ ]/.test(e),r=/^ /.test(e)&&/ $/.test(e);return n&&r&&(e=e.substring(1,e.length-1)),e=f(e,!0),{type:`codespan`,raw:t[0],text:e}}}br(e){let t=this.rules.inline.br.exec(e);if(t)return{type:`br`,raw:t[0]}}del(e){let t=this.rules.inline.del.exec(e);if(t)return{type:`del`,raw:t[0],text:t[2],tokens:this.lexer.inlineTokens(t[2])}}autolink(e){let t=this.rules.inline.autolink.exec(e);if(t){let e,n;return t[2]===`@`?(e=f(t[1]),n=`mailto:`+e):(e=f(t[1]),n=e),{type:`link`,raw:t[0],text:e,href:n,tokens:[{type:`text`,raw:e,text:e}]}}}url(e){let t;if(t=this.rules.inline.url.exec(e)){let e,n;if(t[2]===`@`)e=f(t[0]),n=`mailto:`+e;else{let r;do r=t[0],t[0]=this.rules.inline._backpedal.exec(t[0])?.[0]??``;while(r!==t[0]);e=f(t[0]),n=t[1]===`www.`?`http://`+t[0]:t[0]}return{type:`link`,raw:t[0],text:e,href:n,tokens:[{type:`text`,raw:e,text:e}]}}}inlineText(e){let t=this.rules.inline.text.exec(e);if(t){let e;return e=this.lexer.state.inRawBlock?t[0]:f(t[0]),{type:`text`,raw:t[0],text:e}}}},ie=/^(?: *(?:\n|$))+/,ae=/^( {4}[^\n]+(?:\n(?: *(?:\n|$))*)?)+/,oe=/^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/,x=/^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/,se=/^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/,S=/(?:[*+-]|\d{1,9}[.)])/,C=m(/^(?!bull |blockCode|fences|blockquote|heading|html)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html))+?)\n {0,3}(=+|-+) *(?:\n+|$)/).replace(/bull/g,S).replace(/blockCode/g,/ {4}/).replace(/fences/g,/ {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g,/ {0,3}>/).replace(/heading/g,/ {0,3}#{1,6}/).replace(/html/g,/ {0,3}<[^\n>]+>\n/).getRegex(),w=/^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table| +\n)[^\n]+)*)/,ce=/^[^\n]+/,T=/(?!\s*\])(?:\\.|[^\[\]\\])+/,le=m(/^ {0,3}\[(label)\]: *(?:\n *)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n *)?| *\n *)(title))? *(?:\n+|$)/).replace(`label`,T).replace(`title`,/(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(),ue=m(/^( {0,3}bull)([ \t][^\n]+?)?(?:\n|$)/).replace(/bull/g,S).getRegex(),E=`address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul`,D=/<!--(?:-?>|[\s\S]*?(?:-->|$))/,de=m(`^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n+|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>\\n*|$)|<![A-Z][\\s\\S]*?(?:>\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n *)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n *)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n *)+\\n|$))`,`i`).replace(`comment`,D).replace(`tag`,E).replace(`attribute`,/ +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(),O=m(w).replace(`hr`,x).replace(`heading`,` {0,3}#{1,6}(?:\\s|$)`).replace(`|lheading`,``).replace(`|table`,``).replace(`blockquote`,` {0,3}>`).replace(`fences`," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace(`list`,` {0,3}(?:[*+-]|1[.)]) `).replace(`html`,`</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)`).replace(`tag`,E).getRegex(),k={blockquote:m(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace(`paragraph`,O).getRegex(),code:ae,def:le,fences:oe,heading:se,hr:x,html:de,lheading:C,list:ue,newline:ie,paragraph:O,table:g,text:ce},A=m(`^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)`).replace(`hr`,x).replace(`heading`,` {0,3}#{1,6}(?:\\s|$)`).replace(`blockquote`,` {0,3}>`).replace(`code`,` {4}[^\\n]`).replace(`fences`," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace(`list`,` {0,3}(?:[*+-]|1[.)]) `).replace(`html`,`</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)`).replace(`tag`,E).getRegex(),fe={...k,table:A,paragraph:m(w).replace(`hr`,x).replace(`heading`,` {0,3}#{1,6}(?:\\s|$)`).replace(`|lheading`,``).replace(`table`,A).replace(`blockquote`,` {0,3}>`).replace(`fences`," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace(`list`,` {0,3}(?:[*+-]|1[.)]) `).replace(`html`,`</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)`).replace(`tag`,E).getRegex()},pe={...k,html:m(`^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:"[^"]*"|'[^']*'|\\s[^'"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))`).replace(`comment`,D).replace(/tag/g,`(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b`).getRegex(),def:/^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,heading:/^(#{1,6})(.*)(?:\n+|$)/,fences:g,lheading:/^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/,paragraph:m(w).replace(`hr`,x).replace(`heading`,` *#{1,6} *[^
]`).replace(`lheading`,C).replace(`|table`,``).replace(`blockquote`,` {0,3}>`).replace(`|fences`,``).replace(`|list`,``).replace(`|html`,``).replace(`|tag`,``).getRegex()},j=/^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/,me=/^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/,he=/^( {2,}|\\)\n(?!\s*$)/,ge=/^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/,M=`\\p{P}\\p{S}`,_e=m(/^((?![*_])[\spunctuation])/,`u`).replace(/punctuation/g,M).getRegex(),ve=/\[[^[\]]*?\]\([^\(\)]*?\)|`[^`]*?`|<[^<>]*?>/g,ye=m(/^(?:\*+(?:((?!\*)[punct])|[^\s*]))|^_+(?:((?!_)[punct])|([^\s_]))/,`u`).replace(/punct/g,M).getRegex(),be=m(`^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)[punct](\\*+)(?=[\\s]|$)|[^punct\\s](\\*+)(?!\\*)(?=[punct\\s]|$)|(?!\\*)[punct\\s](\\*+)(?=[^punct\\s])|[\\s](\\*+)(?!\\*)(?=[punct])|(?!\\*)[punct](\\*+)(?!\\*)(?=[punct])|[^punct\\s](\\*+)(?=[^punct\\s])`,`gu`).replace(/punct/g,M).getRegex(),xe=m(`^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)[punct](_+)(?=[\\s]|$)|[^punct\\s](_+)(?!_)(?=[punct\\s]|$)|(?!_)[punct\\s](_+)(?=[^punct\\s])|[\\s](_+)(?!_)(?=[punct])|(?!_)[punct](_+)(?!_)(?=[punct])`,`gu`).replace(/punct/g,M).getRegex(),Se=m(/\\([punct])/,`gu`).replace(/punct/g,M).getRegex(),Ce=m(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace(`scheme`,/[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace(`email`,/[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(),we=m(D).replace(`(?:-->|$)`,`-->`).getRegex(),Te=m(`^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>`).replace(`comment`,we).replace(`attribute`,/\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(),N=/(?:\[(?:\\.|[^\[\]\\])*\]|\\.|`[^`]*`|[^\[\]\\`])*?/,Ee=m(/^!?\[(label)\]\(\s*(href)(?:\s+(title))?\s*\)/).replace(`label`,N).replace(`href`,/<(?:\\.|[^\n<>\\])+>|[^\s\x00-\x1f]*/).replace(`title`,/"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(),P=m(/^!?\[(label)\]\[(ref)\]/).replace(`label`,N).replace(`ref`,T).getRegex(),F=m(/^!?\[(ref)\](?:\[\])?/).replace(`ref`,T).getRegex(),I={_backpedal:g,anyPunctuation:Se,autolink:Ce,blockSkip:ve,br:he,code:me,del:g,emStrongLDelim:ye,emStrongRDelimAst:be,emStrongRDelimUnd:xe,escape:j,link:Ee,nolink:F,punctuation:_e,reflink:P,reflinkSearch:m(`reflink|nolink(?!\\()`,`g`).replace(`reflink`,P).replace(`nolink`,F).getRegex(),tag:Te,text:ge,url:g},De={...I,link:m(/^!?\[(label)\]\((.*?)\)/).replace(`label`,N).getRegex(),reflink:m(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace(`label`,N).getRegex()},L={...I,escape:m(j).replace(`])`,`~|])`).getRegex(),url:m(/^((?:ftp|https?):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/,`i`).replace(`email`,/[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(),_backpedal:/(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/,del:/^(~~?)(?=[^\s~])([\s\S]*?[^\s~])\1(?=[^~]|$)/,text:/^([`~]+|[^`~])(?:(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|https?:\/\/|ftp:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/},Oe={...L,br:m(he).replace(`{2,}`,`*`).getRegex(),text:m(L.text).replace(`\\b_`,`\\b_| {2,}\\n`).replace(/\{2,\}/g,`*`).getRegex()},R={normal:k,gfm:fe,pedantic:pe},z={normal:I,gfm:L,breaks:Oe,pedantic:De},B=class e{tokens;options;state;tokenizer;inlineQueue;constructor(e){this.tokens=[],this.tokens.links=Object.create(null),this.options=e||i,this.options.tokenizer=this.options.tokenizer||new b,this.tokenizer=this.options.tokenizer,this.tokenizer.options=this.options,this.tokenizer.lexer=this,this.inlineQueue=[],this.state={inLink:!1,inRawBlock:!1,top:!0};let t={block:R.normal,inline:z.normal};this.options.pedantic?(t.block=R.pedantic,t.inline=z.pedantic):this.options.gfm&&(t.block=R.gfm,t.inline=this.options.breaks?z.breaks:z.gfm),this.tokenizer.rules=t}static get rules(){return{block:R,inline:z}}static lex(t,n){return new e(n).lex(t)}static lexInline(t,n){return new e(n).inlineTokens(t)}lex(e){e=e.replace(/\r\n|\r/g,`
`),this.blockTokens(e,this.tokens);for(let e=0;e<this.inlineQueue.length;e++){let t=this.inlineQueue[e];this.inlineTokens(t.src,t.tokens)}return this.inlineQueue=[],this.tokens}blockTokens(e,t=[]){e=this.options.pedantic?e.replace(/\t/g,`    `).replace(/^ +$/gm,``):e.replace(/^( *)(\t+)/gm,(e,t,n)=>t+`    `.repeat(n.length));let n,r,i,a;for(;e;)if(!(this.options.extensions&&this.options.extensions.block&&this.options.extensions.block.some(r=>(n=r.call({lexer:this},e,t))?(e=e.substring(n.raw.length),t.push(n),!0):!1))){if(n=this.tokenizer.space(e))e=e.substring(n.raw.length),n.raw.length===1&&t.length>0?t[t.length-1].raw+=`
`:t.push(n);else if(n=this.tokenizer.code(e))e=e.substring(n.raw.length),r=t[t.length-1],r&&(r.type===`paragraph`||r.type===`text`)?(r.raw+=`
`+n.raw,r.text+=`
`+n.text,this.inlineQueue[this.inlineQueue.length-1].src=r.text):t.push(n);else if(n=this.tokenizer.fences(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.heading(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.hr(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.blockquote(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.list(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.html(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.def(e))e=e.substring(n.raw.length),r=t[t.length-1],r&&(r.type===`paragraph`||r.type===`text`)?(r.raw+=`
`+n.raw,r.text+=`
`+n.raw,this.inlineQueue[this.inlineQueue.length-1].src=r.text):this.tokens.links[n.tag]||(this.tokens.links[n.tag]={href:n.href,title:n.title});else if(n=this.tokenizer.table(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.lheading(e))e=e.substring(n.raw.length),t.push(n);else{if(i=e,this.options.extensions&&this.options.extensions.startBlock){let t=1/0,n=e.slice(1),r;this.options.extensions.startBlock.forEach(e=>{r=e.call({lexer:this},n),typeof r==`number`&&r>=0&&(t=Math.min(t,r))}),t<1/0&&t>=0&&(i=e.substring(0,t+1))}if(this.state.top&&(n=this.tokenizer.paragraph(i)))r=t[t.length-1],a&&r.type===`paragraph`?(r.raw+=`
`+n.raw,r.text+=`
`+n.text,this.inlineQueue.pop(),this.inlineQueue[this.inlineQueue.length-1].src=r.text):t.push(n),a=i.length!==e.length,e=e.substring(n.raw.length);else if(n=this.tokenizer.text(e))e=e.substring(n.raw.length),r=t[t.length-1],r&&r.type===`text`?(r.raw+=`
`+n.raw,r.text+=`
`+n.text,this.inlineQueue.pop(),this.inlineQueue[this.inlineQueue.length-1].src=r.text):t.push(n);else if(e){let t=`Infinite loop on byte: `+e.charCodeAt(0);if(this.options.silent){console.error(t);break}throw Error(t)}}}return this.state.top=!0,t}inline(e,t=[]){return this.inlineQueue.push({src:e,tokens:t}),t}inlineTokens(e,t=[]){let n,r,i,a=e,o,s,c;if(this.tokens.links){let e=Object.keys(this.tokens.links);if(e.length>0)for(;(o=this.tokenizer.rules.inline.reflinkSearch.exec(a))!=null;)e.includes(o[0].slice(o[0].lastIndexOf(`[`)+1,-1))&&(a=a.slice(0,o.index)+`[`+`a`.repeat(o[0].length-2)+`]`+a.slice(this.tokenizer.rules.inline.reflinkSearch.lastIndex))}for(;(o=this.tokenizer.rules.inline.blockSkip.exec(a))!=null;)a=a.slice(0,o.index)+`[`+`a`.repeat(o[0].length-2)+`]`+a.slice(this.tokenizer.rules.inline.blockSkip.lastIndex);for(;(o=this.tokenizer.rules.inline.anyPunctuation.exec(a))!=null;)a=a.slice(0,o.index)+`++`+a.slice(this.tokenizer.rules.inline.anyPunctuation.lastIndex);for(;e;)if(s||(c=``),s=!1,!(this.options.extensions&&this.options.extensions.inline&&this.options.extensions.inline.some(r=>(n=r.call({lexer:this},e,t))?(e=e.substring(n.raw.length),t.push(n),!0):!1))){if(n=this.tokenizer.escape(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.tag(e))e=e.substring(n.raw.length),r=t[t.length-1],r&&n.type===`text`&&r.type===`text`?(r.raw+=n.raw,r.text+=n.text):t.push(n);else if(n=this.tokenizer.link(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.reflink(e,this.tokens.links))e=e.substring(n.raw.length),r=t[t.length-1],r&&n.type===`text`&&r.type===`text`?(r.raw+=n.raw,r.text+=n.text):t.push(n);else if(n=this.tokenizer.emStrong(e,a,c))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.codespan(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.br(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.del(e))e=e.substring(n.raw.length),t.push(n);else if(n=this.tokenizer.autolink(e))e=e.substring(n.raw.length),t.push(n);else if(!this.state.inLink&&(n=this.tokenizer.url(e)))e=e.substring(n.raw.length),t.push(n);else{if(i=e,this.options.extensions&&this.options.extensions.startInline){let t=1/0,n=e.slice(1),r;this.options.extensions.startInline.forEach(e=>{r=e.call({lexer:this},n),typeof r==`number`&&r>=0&&(t=Math.min(t,r))}),t<1/0&&t>=0&&(i=e.substring(0,t+1))}if(n=this.tokenizer.inlineText(i))e=e.substring(n.raw.length),n.raw.slice(-1)!==`_`&&(c=n.raw.slice(-1)),s=!0,r=t[t.length-1],r&&r.type===`text`?(r.raw+=n.raw,r.text+=n.text):t.push(n);else if(e){let t=`Infinite loop on byte: `+e.charCodeAt(0);if(this.options.silent){console.error(t);break}throw Error(t)}}}return t}},V=class{options;constructor(e){this.options=e||i}code(e,t,n){let r=(t||``).match(/^\S*/)?.[0];return e=e.replace(/\n$/,``)+`
`,r?`<pre><code class="language-`+f(r)+`">`+(n?e:f(e,!0))+`</code></pre>
`:`<pre><code>`+(n?e:f(e,!0))+`</code></pre>
`}blockquote(e){return`<blockquote>\n${e}</blockquote>\n`}html(e,t){return e}heading(e,t,n){return`<h${t}>${e}</h${t}>\n`}hr(){return`<hr>
`}list(e,t,n){let r=t?`ol`:`ul`,i=t&&n!==1?` start="`+n+`"`:``;return`<`+r+i+`>
`+e+`</`+r+`>
`}listitem(e,t,n){return`<li>${e}</li>\n`}checkbox(e){return`<input `+(e?`checked="" `:``)+`disabled="" type="checkbox">`}paragraph(e){return`<p>${e}</p>\n`}table(e,t){return t&&=`<tbody>${t}</tbody>`,`<table>
<thead>
`+e+`</thead>
`+t+`</table>
`}tablerow(e){return`<tr>\n${e}</tr>\n`}tablecell(e,t){let n=t.header?`th`:`td`;return(t.align?`<${n} align="${t.align}">`:`<${n}>`)+e+`</${n}>\n`}strong(e){return`<strong>${e}</strong>`}em(e){return`<em>${e}</em>`}codespan(e){return`<code>${e}</code>`}br(){return`<br>`}del(e){return`<del>${e}</del>`}link(e,t,n){let r=h(e);if(r===null)return n;e=r;let i=`<a href="`+e+`"`;return t&&(i+=` title="`+t+`"`),i+=`>`+n+`</a>`,i}image(e,t,n){let r=h(e);if(r===null)return n;e=r;let i=`<img src="${e}" alt="${n}"`;return t&&(i+=` title="${t}"`),i+=`>`,i}text(e){return e}},H=class{strong(e){return e}em(e){return e}codespan(e){return e}del(e){return e}html(e){return e}text(e){return e}link(e,t,n){return``+n}image(e,t,n){return``+n}br(){return``}},U=class e{options;renderer;textRenderer;constructor(e){this.options=e||i,this.options.renderer=this.options.renderer||new V,this.renderer=this.options.renderer,this.renderer.options=this.options,this.textRenderer=new H}static parse(t,n){return new e(n).parse(t)}static parseInline(t,n){return new e(n).parseInline(t)}parse(e,t=!0){let n=``;for(let r=0;r<e.length;r++){let i=e[r];if(this.options.extensions&&this.options.extensions.renderers&&this.options.extensions.renderers[i.type]){let e=i,t=this.options.extensions.renderers[e.type].call({parser:this},e);if(t!==!1||![`space`,`hr`,`heading`,`code`,`table`,`blockquote`,`list`,`html`,`paragraph`,`text`].includes(e.type)){n+=t||``;continue}}switch(i.type){case`space`:continue;case`hr`:n+=this.renderer.hr();continue;case`heading`:{let e=i;n+=this.renderer.heading(this.parseInline(e.tokens),e.depth,ee(this.parseInline(e.tokens,this.textRenderer)));continue}case`code`:{let e=i;n+=this.renderer.code(e.text,e.lang,!!e.escaped);continue}case`table`:{let e=i,t=``,r=``;for(let t=0;t<e.header.length;t++)r+=this.renderer.tablecell(this.parseInline(e.header[t].tokens),{header:!0,align:e.align[t]});t+=this.renderer.tablerow(r);let a=``;for(let t=0;t<e.rows.length;t++){let n=e.rows[t];r=``;for(let t=0;t<n.length;t++)r+=this.renderer.tablecell(this.parseInline(n[t].tokens),{header:!1,align:e.align[t]});a+=this.renderer.tablerow(r)}n+=this.renderer.table(t,a);continue}case`blockquote`:{let e=i,t=this.parse(e.tokens);n+=this.renderer.blockquote(t);continue}case`list`:{let e=i,t=e.ordered,r=e.start,a=e.loose,o=``;for(let t=0;t<e.items.length;t++){let n=e.items[t],r=n.checked,i=n.task,s=``;if(n.task){let e=this.renderer.checkbox(!!r);a?n.tokens.length>0&&n.tokens[0].type===`paragraph`?(n.tokens[0].text=e+` `+n.tokens[0].text,n.tokens[0].tokens&&n.tokens[0].tokens.length>0&&n.tokens[0].tokens[0].type===`text`&&(n.tokens[0].tokens[0].text=e+` `+n.tokens[0].tokens[0].text)):n.tokens.unshift({type:`text`,text:e+` `}):s+=e+` `}s+=this.parse(n.tokens,a),o+=this.renderer.listitem(s,i,!!r)}n+=this.renderer.list(o,t,r);continue}case`html`:{let e=i;n+=this.renderer.html(e.text,e.block);continue}case`paragraph`:{let e=i;n+=this.renderer.paragraph(this.parseInline(e.tokens));continue}case`text`:{let a=i,o=a.tokens?this.parseInline(a.tokens):a.text;for(;r+1<e.length&&e[r+1].type===`text`;)a=e[++r],o+=`
`+(a.tokens?this.parseInline(a.tokens):a.text);n+=t?this.renderer.paragraph(o):o;continue}default:{let e=`Token with "`+i.type+`" type was not found.`;if(this.options.silent)return console.error(e),``;throw Error(e)}}}return n}parseInline(e,t){t||=this.renderer;let n=``;for(let r=0;r<e.length;r++){let i=e[r];if(this.options.extensions&&this.options.extensions.renderers&&this.options.extensions.renderers[i.type]){let e=this.options.extensions.renderers[i.type].call({parser:this},i);if(e!==!1||![`escape`,`html`,`link`,`image`,`strong`,`em`,`codespan`,`br`,`del`,`text`].includes(i.type)){n+=e||``;continue}}switch(i.type){case`escape`:{let e=i;n+=t.text(e.text);break}case`html`:{let e=i;n+=t.html(e.text);break}case`link`:{let e=i;n+=t.link(e.href,e.title,this.parseInline(e.tokens,t));break}case`image`:{let e=i;n+=t.image(e.href,e.title,e.text);break}case`strong`:{let e=i;n+=t.strong(this.parseInline(e.tokens,t));break}case`em`:{let e=i;n+=t.em(this.parseInline(e.tokens,t));break}case`codespan`:{let e=i;n+=t.codespan(e.text);break}case`br`:n+=t.br();break;case`del`:{let e=i;n+=t.del(this.parseInline(e.tokens,t));break}case`text`:{let e=i;n+=t.text(e.text);break}default:{let e=`Token with "`+i.type+`" type was not found.`;if(this.options.silent)return console.error(e),``;throw Error(e)}}}return n}},W=class{options;constructor(e){this.options=e||i}static passThroughHooks=new Set([`preprocess`,`postprocess`,`processAllTokens`]);preprocess(e){return e}postprocess(e){return e}processAllTokens(e){return e}},G=new class{defaults=r();options=this.setOptions;parse=this.#e(B.lex,U.parse);parseInline=this.#e(B.lexInline,U.parseInline);Parser=U;Renderer=V;TextRenderer=H;Lexer=B;Tokenizer=b;Hooks=W;constructor(...e){this.use(...e)}walkTokens(e,t){let n=[];for(let r of e)switch(n=n.concat(t.call(this,r)),r.type){case`table`:{let e=r;for(let r of e.header)n=n.concat(this.walkTokens(r.tokens,t));for(let r of e.rows)for(let e of r)n=n.concat(this.walkTokens(e.tokens,t));break}case`list`:{let e=r;n=n.concat(this.walkTokens(e.items,t));break}default:{let e=r;this.defaults.extensions?.childTokens?.[e.type]?this.defaults.extensions.childTokens[e.type].forEach(r=>{let i=e[r].flat(1/0);n=n.concat(this.walkTokens(i,t))}):e.tokens&&(n=n.concat(this.walkTokens(e.tokens,t)))}}return n}use(...e){let t=this.defaults.extensions||{renderers:{},childTokens:{}};return e.forEach(e=>{let n={...e};if(n.async=this.defaults.async||n.async||!1,e.extensions&&(e.extensions.forEach(e=>{if(!e.name)throw Error(`extension name required`);if(`renderer`in e){let n=t.renderers[e.name];n?t.renderers[e.name]=function(...t){let r=e.renderer.apply(this,t);return r===!1&&(r=n.apply(this,t)),r}:t.renderers[e.name]=e.renderer}if(`tokenizer`in e){if(!e.level||e.level!==`block`&&e.level!==`inline`)throw Error(`extension level must be 'block' or 'inline'`);let n=t[e.level];n?n.unshift(e.tokenizer):t[e.level]=[e.tokenizer],e.start&&(e.level===`block`?t.startBlock?t.startBlock.push(e.start):t.startBlock=[e.start]:e.level===`inline`&&(t.startInline?t.startInline.push(e.start):t.startInline=[e.start]))}`childTokens`in e&&e.childTokens&&(t.childTokens[e.name]=e.childTokens)}),n.extensions=t),e.renderer){let t=this.defaults.renderer||new V(this.defaults);for(let n in e.renderer){if(!(n in t))throw Error(`renderer '${n}' does not exist`);if(n===`options`)continue;let r=n,i=e.renderer[r],a=t[r];t[r]=(...e)=>{let n=i.apply(t,e);return n===!1&&(n=a.apply(t,e)),n||``}}n.renderer=t}if(e.tokenizer){let t=this.defaults.tokenizer||new b(this.defaults);for(let n in e.tokenizer){if(!(n in t))throw Error(`tokenizer '${n}' does not exist`);if([`options`,`rules`,`lexer`].includes(n))continue;let r=n,i=e.tokenizer[r],a=t[r];t[r]=(...e)=>{let n=i.apply(t,e);return n===!1&&(n=a.apply(t,e)),n}}n.tokenizer=t}if(e.hooks){let t=this.defaults.hooks||new W;for(let n in e.hooks){if(!(n in t))throw Error(`hook '${n}' does not exist`);if(n===`options`)continue;let r=n,i=e.hooks[r],a=t[r];t[r]=W.passThroughHooks.has(n)?e=>{if(this.defaults.async)return Promise.resolve(i.call(t,e)).then(e=>a.call(t,e));let n=i.call(t,e);return a.call(t,n)}:(...e)=>{let n=i.apply(t,e);return n===!1&&(n=a.apply(t,e)),n}}n.hooks=t}if(e.walkTokens){let t=this.defaults.walkTokens,r=e.walkTokens;n.walkTokens=function(e){let n=[];return n.push(r.call(this,e)),t&&(n=n.concat(t.call(this,e))),n}}this.defaults={...this.defaults,...n}}),this}setOptions(e){return this.defaults={...this.defaults,...e},this}lexer(e,t){return B.lex(e,t??this.defaults)}parser(e,t){return U.parse(e,t??this.defaults)}#e(e,t){return(n,r)=>{let i={...r},a={...this.defaults,...i};this.defaults.async===!0&&i.async===!1&&(a.silent||console.warn(`marked(): The async option was set to true by an extension. The async: false option sent to parse will be ignored.`),a.async=!0);let o=this.#t(!!a.silent,!!a.async);if(n==null)return o(Error(`marked(): input parameter is undefined or null`));if(typeof n!=`string`)return o(Error(`marked(): input parameter is of type `+Object.prototype.toString.call(n)+`, string expected`));if(a.hooks&&(a.hooks.options=a),a.async)return Promise.resolve(a.hooks?a.hooks.preprocess(n):n).then(t=>e(t,a)).then(e=>a.hooks?a.hooks.processAllTokens(e):e).then(e=>a.walkTokens?Promise.all(this.walkTokens(e,a.walkTokens)).then(()=>e):e).then(e=>t(e,a)).then(e=>a.hooks?a.hooks.postprocess(e):e).catch(o);try{a.hooks&&(n=a.hooks.preprocess(n));let r=e(n,a);a.hooks&&(r=a.hooks.processAllTokens(r)),a.walkTokens&&this.walkTokens(r,a.walkTokens);let i=t(r,a);return a.hooks&&(i=a.hooks.postprocess(i)),i}catch(e){return o(e)}}}#t(e,t){return n=>{if(n.message+=`
Please report this to https://github.com/markedjs/marked.`,e){let e=`<p>An error occurred:</p><pre>`+f(n.message+``,!0)+`</pre>`;return t?Promise.resolve(e):e}if(t)return Promise.reject(n);throw n}}};function K(e,t){return G.parse(e,t)}K.options=K.setOptions=function(e){return G.setOptions(e),K.defaults=G.defaults,a(K.defaults),K},K.getDefaults=r,K.defaults=i,K.use=function(...e){return G.use(...e),K.defaults=G.defaults,a(K.defaults),K},K.walkTokens=function(e,t){return G.walkTokens(e,t)},K.parseInline=G.parseInline,K.Parser=U,K.parser=U.parse,K.Renderer=V,K.TextRenderer=H,K.Lexer=B,K.lexer=B.lex,K.Tokenizer=b,K.Hooks=W,K.parse=K,K.options,K.setOptions,K.use,K.walkTokens,K.parseInline,U.parse,B.lex;var ke=`# "Nasıl yaptık" sayfası (taslak v1)

> Hedef okur: teknik olmayan biri. Her bölüm aynı kalıpta: **Ne**, **Neden**, **Nasıl**, **Ne çıktı**, **Sınırı ne**. Ayrıntı isteyen
> için her bölümün sonunda kod dosyası ve yöntem belgesi bağlantısı. Kodun tamamı açık.

---

## Kısaca

Bu çalışma beş adımdan oluşuyor:

1. **Veri:** 25'ten fazla açık kaynaktan İstanbul'un mahalle, bina, nüfus, yol, hastane ve açık alan verisi toplandı, temizlendi,
   959 mahallelik tek bir tabloda birleştirildi.
2. **Sarsıntı:** Bir depremde her mahallenin ne kadar sarsılacağını hesaplayan modeller gerçek deprem kayıtlarıyla sınandı.
3. **Hasar ve sınav:** Binaların bu sarsıntıda nasıl davranacağını hesaplayan yöntemler 6 Şubat 2023 depremiyle sınandı; büyük
   depremi tutarlı biçimde eksik tahmin ettikleri için ölüm sayısı yayımlamamaya karar verildi.
4. **Kapasite:** Hayatta kalanların ilk gece nereye gidebileceği bir optimizasyon problemi olarak çözüldü; ulaşım, haberleşme,
   hastane ve barınma ihtiyacı hesaplandı.
5. **Görselleştirme:** Sonuçlar gerçek bina tabanları ve makine öğrenmesiyle tahmin edilen yüksekliklerle 3B haritaya taşındı.

---

## 1. Veri: nereden geldi

| Ne | Kaynak | Ne için kullanıldı |
|---|---|---|
| Mahalle nüfusu (2025) | TÜİK, Adrese Dayalı Nüfus Kayıt Sistemi | Her hesabın temeli: kaç kişi |
| Bina stoğu (2017): yaş ve kat sınıfları | İBB Açık Veri | Hasar sınıfları, kat dağılımı |
| İBB deprem senaryosu (Mw 7,5 gece) | İBB Açık Veri | Karşılaştırma, barınma ihtiyacı |
| Bina tabanları (1,15 milyon) | Overture Maps (Eylül 2026) | Bina şekli ve sayısı, 3B harita |
| Yol ağı, mahalle sınırları, park ve hastane etiketleri | OpenStreetMap | Mesafe, erişim, toplanma alanları |
| Köprü ve viyadükler, acil ulaşım yolları | İBB Açık Veri | Yol ağının kritik parçaları |
| Açık ve yeşil alanlar | İBB Açık Veri + OpenStreetMap | Toplanma alanı adayları |
| Hastaneler, itfaiye istasyonları | İBB Açık Veri; il yatak toplamı TBMM tutanağı | Kapasite ve erişim |
| Zemin (Vs30) | ABD Jeoloji Araştırmaları Kurumu (USGS) | Sarsıntının yerel büyümesi |
| Marmara fay izleri | GEM küresel aktif faylar | Deprem senaryoları |
| 2025 Silivri ve 2023 depremlerinin kayıtları | USGS ShakeMap | Modelleri sınamak |
| 1999 İzmit kayıtları | KOERI (2010) raporu | Modelleri sınamak |
| Uydu yapılaşma ve nüfus katmanları | Avrupa Komisyonu GHSL | Bina yaşı vekili, 6 Şubat nüfusu |
| 6 Şubat hasar ve kayıp sayıları | AFAD, Strateji ve Bütçe Başkanlığı (2023) | Sınav |
| Yapı ruhsatları (2010–2024), sosyal yardım, hane büyüklüğü | İBB Açık Veri | Dönüşüm hızı, ihtiyaç |

**Sınırı ne:** Resmî AFAD toplanma alanı listesi, İBB mikrobölgeleme (zemin) haritası ve tesis bazında hastane yatak sayıları toplu
olarak açık değil; yerlerine açık veriden türetilmiş vekiller kullanıldı ve her biri işaretlendi.

---

## 2. Temizlik: neyi, nasıl düzelttik

**Ne:** Ham veri hatalarla gelir. Her düzeltme bir "karar" olarak kayda geçti (55 karar), her ara ürün otomatik kontrollerden geçti
(56 kontrol, hepsi geçiyor). Bütün veri hattı ham dosyalardan yaklaşık 2,5 dakikada yeniden üretilebiliyor.

**Örnekler:**

| Sorun | Ne yaptık | Neden önemli |
|---|---|---|
| Excel, "19 Mayıs" ve "15 Temmuz" mahalle adlarını tarihe çevirmiş | Adlar geri onarıldı | Onarılmasa 5 mahallenin yardım verisi kaybolurdu |
| İBB dosyaları Türkçe karakter kodlamasıyla (cp1254) geliyor | Doğru kodlamayla okundu | "HEYBELİADA" bozulup eşleşmeyi kırıyordu |
| Muhtarlık listesinde "Mahalle Adı" sütunu yanlış mahalleyi gösteriyor (115 kayıt) | Ad, muhtarlığın kendi adından türetildi | Mahalle eşleşmesi doğru olsun |
| OpenStreetMap'te İstanbul sınırı denizi de kapsıyor (11.281 km²) | Kara sınırı ayrıca üretildi | Deniz alanı yoğunluk hesabını bozardı |
| Aynı hastanenin acil, poliklinik, ek bina kayıtları ayrı ayrı (472 kayıt) | 120 m içindekiler tek tesiste birleşti (328) | Kapasite çift sayılmasın |
| Hastane listesinde "istanbul Şehir", "Mega Şehir" gibi 56 sahte "Şehir Hastanesi" kaydı | Çıkarıldı | Yatak dağıtımını ve "depreme dayanıklı hastane" varsayımını bozuyordu |
| İtfaiye verisinde enlem ve boylam sütunları ters etiketli | Değer aralığına göre düzeltildi | İstasyonlar denizde görünüyordu |
| Aynı park İBB'de ve OSM'de (OSM'de parça parça) ayrı çizilmiş | 11.390 parça 9.144 alana birleşti | Toplanma kapasitesi şişmesin |
| Refüj, kavşak, metro çıkışı "yeşil alan" görünüyor (539) | Toplanma alanından çıkarıldı | Trafik adası toplanma alanı değil |
| 2017'den sonra kurulan mahalleler (ör. 15 Temmuz, 5. Levent) | Eski ana mahalleyle birleştirildi | Bina verisi eski sınırlara göre |

**Birleştirme:** Analiz birimi mahalle (959). İBB 2017, TÜİK 2025 ve OSM 2026 adları aynı değil; eşleştirme önce resmî mahalle koduyla
(UAVT), sonra ad, muhtarlık konumu ve gerektiğinde bulanık ad eşleştirmesiyle yapıldı; her eşleşmenin yöntemi ve güveni kayıtlı.

Kod: \`scripts/00–09\`, rapor: \`docs/VERI_RAPORU.md\`.

---

## 3. Sarsıntı: yer hareketi modeli

**Ne:** Bir depremde bir noktanın ne kadar sarsılacağını tahmin eden denklemler ("yer hareketi modeli"). Girdi: depremin büyüklüğü,
faya uzaklık, zemin. Çıktı: yer ivmesi.

**Neden:** Her şey sarsıntıyla başlar; yanlış sarsıntı her sonraki hesabı yanlış yapar.

**Nasıl:**
- Dünyada yaygın kullanılan 8 denklem (İstanbul senaryo çalışmalarında kullanılanlar dahil) aynı anda çalıştırıldı.
- Her biri iki gerçek depremin kayıtlarıyla sınandı: 2025 Silivri (İstanbul'daki 47 istasyon) ve 1999 İzmit (25 istasyon).
- Kayıtlara ne kadar uyduklarına göre ağırlık verildi; sonuç tek bir denklem değil, ağırlıklı bir karışım.
- Aynı deprem 1.000 kez üretildi: her seferinde komşu mahallelerin birbirine benzer sarsılması (uzamsal korelasyon) korunarak.
  Böylece "en olası" değerin yanında "kötü bir gece" de görülebiliyor.
- Üç farklı kırılma senaryosu: Orta Marmara (Mw 7,5), Adalar–Çınarcık (Mw 7,4) ve tüm Marmara (Mw 7,7).

**Ne çıktı:** Denklemlerin bazıları 2025 gibi orta büyüklükteki bir depremde sarsıntıyı fazla tahmin ediyor (en büyük fark ~2,3 kat),
1999 gibi büyük bir depremde ise tutarlı; bu, denklemlerin büyük depremler için geliştirilmesinin beklenen bir sonucu. Ağırlıklı karışım
iki depremde de tutarlı.

**Sınırı ne:** Zemin verisi kaba (yaklaşık 900 m çözünürlük); kıyı dolguları gibi yerel etkiler görünmüyor. 2025 orta büyüklükte bir
deprem; büyüklük arttıkça sınama zayıflıyor.

Kod: \`model/yh_*\`, belge: \`docs/YONTEM_1_YER_HAREKETI.md\`.

---

## 4. Hasar ve 6 Şubat sınavı: neden ölüm sayısı yok

**Ne:** Bir binanın belli bir sarsıntıda hafif, orta, ağır hasar görme ya da yıkılma olasılığını veren "kırılganlık eğrileri" ve
yıkılan binada can kaybı oranları. Dünyada ve Türkiye'de senaryo çalışmalarının standart yöntemi.

**Neden sınadık:** Bir modelin büyük bir depremde ne yaptığını görmenin tek yolu onu büyük bir depremle sınamak.

**Nasıl:**
- Önce yöntemi doğru kurduğumuzu kontrol ettik: İBB'nin açık senaryo verisindeki çok ağır hasarlı bina sayısını (13.496) aynı yöntemle
  yeniden ürettik (13.510).
- Sonra yöntemi 6 Şubat 2023'ün gerçek sarsıntısı (USGS), bölgenin gece nüfusu (uydu) ve uydudan görülen bina yaşıyla çalıştırdık.
- Ardından kendi modelimizi dört gerçek depremle (2025 Silivri, 1999 İstanbul, 1999 fay bölgesi, 6 Şubat) ayarlamaya çalıştık:
  sarsıntı süresini, yıkılan binanın yüksekliğine göre ölümcüllüğü ve bölgeler arası bina kalitesi farkını ekledik.

**Ne çıktı:**

| Model | 6 Şubat için tahmin | Gerçek |
|---|---|---|
| Standart kırılganlık yöntemi (KOERI/HAZUS eğrileri) | ~15.400 | 53.537 |
| USGS'nin Türkiye'ye göre ayarlanmış ampirik modeli | ~21.300 | |
| Bu proje, İstanbul depremlerine ayarlı | ~2.200 | |
| Bu proje, dört depreme birlikte ayarlı | ~24.700 | |

En iyi sürüm bile 1999 İstanbul'u yaklaşık 3 kat fazla, 6 Şubat'ı yaklaşık 2 kat eksik tahmin etti ve ölümleri gerçekte olduğundan çok
yığma binalara yükledi. Bunu düzeltmek parametre ayarıyla değil, bina tipine ve kat sayısına göre ayrılmış gerçek hasar verisiyle
mümkün (Bakanlık 2,15 milyon binayı tek tek inceledi; bu veri toplu olarak açık değil).

Büyük, uzun süren depremlerde bütün yöntemlerin kaybı düşük tahmin etmesi literatürde de bilinen bir zorluk.

**Karar:** İstanbul için ölüm sayısı yayımlanmıyor. Hasar modeli yalnızca kaba büyüklük için (hangi mahallede kaç kişi hasarlı binada)
kullanılıyor; toplanma hesabında da sonuç asıl olarak nüfusa ve alana dayanıyor.

Kod: \`model/hs_*\`, \`sinama/\`, belge: \`docs/YONTEM_2_HASAR.md\`.

---

## 5. Toplanma: bir optimizasyon problemi

**Ne:** Deprem gecesi dışarı çıkan herkese yürüme mesafesinde yer var mı?

**Neden basit oran yetmiyor:** "Mahalledeki park alanı ÷ nüfus" yanıltıcı: bir park birden çok mahalleye hizmet eder, insanlar ise
yalnızca yürüyebildikleri yere gider.

**Oyuncak örnek:** Üç sokak (A, B, C; her birinde 100 kişi) ve iki park düşünün: P1 100 kişilik, P2 250 kişilik. Toplam kapasite 350,
toplam insan 300; kağıt üstünde herkese yer var. Ama A ve B yalnızca P1'e yürüyebiliyor, P2 ise yalnızca C'nin yakınında. A ve B'nin 200
kişisi 100 kişilik P1'e sığmaz: **100 kişi yer bulamaz**, bu sırada P2'de 150 kişilik yer boş kalır. Toplam "yeterli" der; yer "yetmez" der.

**Nasıl (gerçek boyutta):**
- İstanbul ~49 bin bina bloğuna (yaklaşık 250 m'lik kareler) bölündü; her bloğun nüfusu yapı hacmine göre dağıtıldı.
- 2.000 m²'den büyük 2.960 açık alan aday (AFAD'ın açıkladığı 3.021 alanla aynı mertebe). Her alanın kullanılabilir kısmı türüne göre:
  saha ve meydan %90, park %60, okul bahçesi %50, koru ve orman %20. Kişi başı 1,5 m².
- Her blok, 1 km yürüme mesafesindeki alanlara atanır; hiçbir alan kapasitesini aşamaz. Amaç önce olabildiğince çok kişiye yer
  bulmak, sonra toplam yürümeyi en aza indirmek. Bu bir "ulaştırma problemi"; yaklaşık 170 bin değişkenli doğrusal program yarım
  saniyede çözülüyor.
- Kaç kişinin dışarı çıkacağı: hasarlı binada yaşayanlar ve sarsıntı arttıkça artan bir korku payı (0,05 g'de %10, 0,30 g'de %80).

**Ne çıktı:** Medyan depremde ilk gece dışarıdaki 9,1 milyon kişiden **2,7 milyonu** 1 km içinde yer bulamıyor.

| Varsayım değişirse | Yer bulamayan |
|---|---|
| Kişi başı 2 m² | 3,4 milyon |
| Yürüme sınırı 1,5 km | 1,6 milyon |
| Dışarı çıkan sayısı yarıya inerse | 0,85 milyon |
| Herkes dışarı çıkarsa | 6,4 milyon |

**Sınırı ne:** "Kaç kişi dışarı çıkar" sonucu en çok belirleyen varsayım; bu yüzden aralık veriliyor. Açık alan katmanı resmî liste değil.

Kod: \`ihtiyac/i01–i02\`, belge: \`docs/YONTEM_5_IHTIYAC.md\`.

---

## 6. Makine öğrenmesi: nerede kullandık, nerede vazgeçtik

**a) Bina yüksekliği (sitede kullanılıyor).** 3B haritadaki binaların yalnızca %4'ünün yüksekliği biliniyor. İstanbul'da kat sayısı
bilinen 72 bin binayla bir model (LightGBM) eğittik. Model her bina için taban alanına, şekline, çevresindeki binalara, uydudan ölçülen
ortalama yüksekliğe ve mahallenin İBB kat dağılımına bakıyor. Sınama, model hiç görmediği ilçelerde yapıldı: kat sınıfını (1–4 / 5–8 / 9+)
%67 doğru buluyor, basit kural %59. Yüksek binaları hâlâ eksik buluyor; haritadaki yükseklikler "tahmini" olarak işaretli.

**b) Açık senaryo verisini anlamak.** İBB'nin açtığı mahalle hasar oranlarını açıklayan bir model kurup hangi bilginin ağır bastığına
baktık (SHAP). Sonuç: senaryodaki hasar dağılımını açık ara faya uzaklık belirliyor; ardından 1980 öncesi bina payı ve 5 kat üstü bina payı geliyor. Hiç görmediği ilçelerde fizik tabanlı hesabımız varyansın %50'sini,
makine öğrenmesiyle birlikte %59'unu açıklıyor; rastgele bölünmüş sınama bu başarıyı yaklaşık 0,1 şişiriyor, bu yüzden ilçe dışı sınama
kullanıldı.

**c) Vazgeçtiğimiz deneme: 6 Şubat'tan öğrenmek.** Avrupa Copernicus hizmetinin uydu görüntülerinden işaretlediği 47 bin binalık hasar
etiketleriyle "hangi bina, ne kadar sarsıntıda yıkıldı" modeli kurmayı denedik. Model hiç görmediği bölgede yıkılan binayı ancak
yazı-turadan biraz iyi ayırt edebildi (AUC 0,54–0,68). Sebep etiketlerdi: her bölge farklı tarihte, farklı görüntüyle işaretlenmişti.
Bu denemeyi sonuçlara katmadık.

**d) Simülatörün hızlı vekili.** 72 saatlik simülatörü taklit eden, tarayıcıda anında çalışan bir model (R² 0,96) kurduk; simülatör ana
anlatıdan çıkınca bu model de sitede kullanılmıyor.

Kod: \`ml/\`, belge: \`docs/YONTEM_4_ML.md\`.

---

## 7. 72 saat simülatörü: nasıl çalışıyor, neden ana anlatıda yok

**Ne:** Depremden sonraki 72 saati 15 dakikalık adımlarla canlandıran bir model. Enkaz altında kalanların zamanla azalan hayatta kalma
şansı, ekiplerin hasarlı yol ağında bir mahalleden ötekine gitmesi, köprü ve enkaz kapanmaları, hastanelerin dolması.

**Nasıl:** Kurbanlar mahalle başına havuzlar halinde, ekipler tek tek ajanlar olarak izleniyor. Hayatta kalma eğrisi geçmiş depremlerin
kurtarma verisinden (Coburn vd. 1992); köprü hasarı HAZUS eğrilerinden. Dört farklı ekip dağıtım kuralı ve bir optimizasyon planı
aynı rastgele depremler üzerinde karşılaştırıldı; sahra hastanelerinin yeri ayrıca optimize edildi.

**Neden ana anlatıda yok:** Simülatörün girdisi, kimin enkaz altında kaldığı. Bu da 6 Şubat sınavını geçemeyen hasar modelinden geliyor.
Mekanizmalar (ör. kalabalıkla tıkanan kurtarma) sağlam, ama mutlak sayılar o güvenilirlikte değil.

Kod: \`sim/\`, belge: \`docs/YONTEM_3_SIMULASYON.md\`.

---

## 8. Esenyurt hesapları

| Kalem | Değer | Nasıl |
|---|---|---|
| Yürünebilir sokak (Turgut Özal) | ~84.000 m² | OSM yol uzunluğu × yol türüne göre genişlik, gece park eden araçlar düşülerek |
| Araç (Esenyurt) | 150–240 bin | TÜİK İstanbul: bin kişiye 241 otomobil; alt sınır 150 |
| İlçe çıkış kapasitesi | ~68 bin araç/saat | Sınırdan çıkan otoyol, ana ve ikincil yolların şerit sayısı × şerit kapasitesi |
| Hastane yatağı | ~720 (bin kişiye 0,7) | İl yatak toplamı, hastane kampüslerinin bina alanına göre dağıtıldı |
| Gereken kamp alanı (Turgut Özal) | 346.050 m² | İBB'nin 7.690 kişilik barınma ihtiyacı × kişi başı 45 m² (Sphere) |

---

## 9. Haritalar

Altlık harita OpenStreetMap verisinden (Protomaps derlemesi, Ekim 2026), sitenin içinden tek dosya olarak sunuluyor. Binalar Overture
tabanları; yükseklikleri 6. bölümdeki modelden (gerçek yüksekliği bilinenlerde o değer). Toplanma akışları 5. bölümdeki optimizasyonun
doğrudan sonucu.

---

## 10. Sınırlılıklar ve dürüstlük notları

- Bu bağımsız bir portföy çalışmasıdır; deprem tahmini yapmaz, resmî kurumların plan ve çalışmalarını değerlendirmez.
- Toplanma sonucu resmî toplanma alanı planının değerlendirmesi değildir; açık veriden türetilmiş potansiyel alanlarla yapılmıştır.
- Ölüm sayısı yayımlanmaz (4. bölüm).
- Toplanma sonucu en çok "kaç kişi dışarı çıkar" varsayımına bağlı; aralık veriliyor.
- Veriler farklı yıllardan: nüfus 2025, açık alan ve yollar 2026, bina yaşı ve kat sınıfları ile İBB deprem senaryosu 2017 bina
  stoğuna dayanıyor. Bu yüzden yaş ve kat oranları "2017 sayımında" diye verildi, kişi/bina hem 2017 sayımıyla hem güncel bina
  tabanlarıyla aralık olarak hesaplandı, barınma ihtiyacı alt sınır kabul edildi. Toplanma hesabı yalnızca 2025 nüfusu ile güncel
  açık alanları kullanıyor; eski bina verisine dayanmıyor.
- Zemin verisi kaba; hastane yatakları il toplamından dağıtılmış tahmin.
- Çalışma sırasında kendi hesaplarımızda bulduğumuz hatalar (ör. bir oranın yanlış nüfusla hesaplanması) düzeltildi ve belgelerde not edildi.

## Yeniden üretim

Bütün kod ve adım sırası depoda (\`docs/ILERLEME.md\`). Ham veri \`scripts/00_indir.py\` ile indirilir; veri hattı tek komutla çalışır.
`,Ae=`# "How we did it" page (English version of NASIL_YAPTIK.md)

> Target reader: someone non-technical. Every section follows the same pattern: **What**, **Why**, **How**, **What came out**,
> **What the limits are**. Each section ends with the code and method document for readers who want detail. All code is open.

---

## In short

The study has five steps:

1. **Data:** Neighbourhood, building, population, road, hospital and open-space data for Istanbul were collected from more than 25 open
   sources, cleaned and joined into a single table of 959 neighbourhoods.
2. **Shaking:** Models that estimate how strongly each neighbourhood would shake were tested against recordings of real earthquakes.
3. **Damage and the test:** Methods that estimate how buildings behave under that shaking were tested against the 6 February 2023
   earthquake; because they consistently underestimated a large earthquake, we decided not to publish death counts.
4. **Capacity:** Where survivors could go on the first night was solved as an optimisation problem; transport, communication, hospital
   and shelter needs were estimated.
5. **Visualisation:** The results were placed on a 3D map with real building footprints and heights estimated with machine learning.

---

## 1. Data: where it came from

| What | Source | Used for |
|---|---|---|
| Neighbourhood population (2025) | TÜİK (Turkish Statistical Institute), address-based population register | The basis of every calculation: how many people |
| Building stock (2017): age and floor classes | Istanbul Metropolitan Municipality (İBB) Open Data | Damage classes, floor distribution |
| İBB earthquake scenario (Mw 7.5, night) | İBB Open Data | Comparison, shelter needs |
| Building footprints (1.15 million) | Overture Maps (September 2026) | Building shape and count, 3D map |
| Road network, neighbourhood boundaries, park and hospital tags | OpenStreetMap | Distance, access, assembly areas |
| Bridges and viaducts, emergency transport routes | İBB Open Data | Critical parts of the road network |
| Open and green spaces | İBB Open Data + OpenStreetMap | Assembly area candidates |
| Hospitals, fire stations | İBB Open Data; provincial bed total from a parliamentary record | Capacity and access |
| Soil (Vs30) | United States Geological Survey (USGS) | Local amplification of shaking |
| Marmara fault traces | GEM Global Active Faults | Earthquake scenarios |
| Recordings of the 2025 Silivri and 2023 earthquakes | USGS ShakeMap | Testing the models |
| 1999 İzmit recordings | KOERI (2010) report | Testing the models |
| Satellite built-up and population layers | European Commission GHSL | Proxy for building age, 6 February population |
| 6 February damage and casualty figures | AFAD, Presidency of Strategy and Budget (2023) | The test |
| Building permits (2010–2024), social assistance, household size | İBB Open Data | Renewal rate, needs |

**Limits:** The official AFAD list of assembly areas, İBB's microzonation (soil) map and per-facility hospital bed counts are not openly
available in bulk; open-data proxies were used instead and each one is marked.

---

## 2. Cleaning: what we fixed and how

**What:** Raw data arrives with errors. Every fix was logged as a "decision" (55 decisions) and every intermediate product passed
automated checks (56 checks, all passing). The whole pipeline can be rebuilt from the raw files in about 2.5 minutes.

**Examples:**

| Problem | What we did | Why it matters |
|---|---|---|
| Excel had turned the neighbourhood names "19 Mayıs" and "15 Temmuz" into dates | Names restored | Otherwise 5 neighbourhoods would lose their assistance data |
| İBB files use a Turkish character encoding (cp1254) | Read with the correct encoding | "HEYBELİADA" was garbled and broke the matching |
| In the headman office list, the "Neighbourhood name" column points to the wrong neighbourhood (115 records) | Name derived from the office's own name | So neighbourhoods match correctly |
| The OpenStreetMap boundary of Istanbul includes the sea (11,281 km²) | A separate land boundary was built | Sea area would distort densities |
| Emergency, outpatient and annex records of the same hospital listed separately (472 records) | Records within 120 m merged into one facility (328) | So capacity is not double counted |
| 56 fake "City Hospital" records in the hospital list, such as "istanbul Şehir" or "Mega Şehir" | Removed | They distorted bed allocation and the "earthquake-resistant hospital" assumption |
| Latitude and longitude columns swapped in the fire station data | Fixed by value range | Stations appeared in the sea |
| The same park drawn separately in İBB and OSM (in pieces in OSM) | 11,390 pieces merged into 9,144 areas | So assembly capacity is not inflated |
| Medians, junctions and metro exits appear as "green space" (539) | Removed from assembly areas | A traffic island is not an assembly area |
| Neighbourhoods created after 2017 (e.g. 15 Temmuz, 5. Levent) | Merged with their former parent neighbourhood | Building data follows the old boundaries |

**Joining:** The unit of analysis is the neighbourhood (959). Names differ between İBB 2017, TÜİK 2025 and OSM 2026; matching used the
official neighbourhood code (UAVT) first, then name, headman office location and, where needed, fuzzy name matching; the method and
confidence of every match are recorded.

Code: \`scripts/00–09\`, report: \`docs/VERI_RAPORU.md\`.

---

## 3. Shaking: the ground-motion model

**What:** Equations that estimate how strongly a point will shake in an earthquake ("ground-motion models"). Inputs: magnitude,
distance to the fault, soil. Output: ground acceleration.

**Why:** Everything starts with shaking; wrong shaking makes every later calculation wrong.

**How:**
- 8 widely used equations (including those used in Istanbul scenario studies) were run side by side.
- Each was tested against recordings of two real earthquakes: 2025 Silivri (47 stations in Istanbul) and 1999 İzmit (25 stations).
- They were weighted by how well they matched the recordings; the result is a weighted mix, not a single equation.
- The same earthquake was generated 1,000 times, each time keeping the fact that neighbouring areas shake similarly (spatial
  correlation). This shows a "bad night" alongside the "most likely" value.
- Three rupture scenarios: Central Marmara (Mw 7.5), Islands–Çınarcık (Mw 7.4) and the whole Marmara (Mw 7.7).

**What came out:** Some equations overestimate shaking in a moderate earthquake like 2025 (largest difference ~2.3×) but are consistent
in a large one like 1999; this is expected, since they were developed for large earthquakes. The weighted mix is consistent for both.

**Limits:** The soil data is coarse (about 900 m resolution); local effects such as coastal fill are not visible. 2025 was a moderate
earthquake; the test gets weaker as magnitude grows.

Code: \`model/yh_*\`, document: \`docs/YONTEM_1_YER_HAREKETI.md\`.

---

## 4. Damage and the 6 February test: why there is no death count

**What:** "Fragility curves" that give the probability of a building suffering light, moderate or heavy damage or collapsing under a
given shaking, and fatality rates in collapsed buildings. The standard method of scenario studies worldwide and in Türkiye.

**Why we tested it:** The only way to see what a model does in a large earthquake is to test it against one.

**How:**
- First we checked that we had implemented the method correctly: we reproduced the number of very heavily damaged buildings in İBB's
  open scenario data (13,496) with the same method (13,510).
- Then we ran the method with the real shaking of 6 February 2023 (USGS), the region's night-time population (satellite) and building
  age seen from satellite.
- Next we tried to calibrate our own model against four real earthquakes (2025 Silivri, 1999 Istanbul, 1999 fault zone, 6 February):
  we added shaking duration, lethality by height of the collapsed building and regional differences in building quality.

**What came out:**

| Model | Estimate for 6 February | Actual |
|---|---|---|
| Standard fragility method (KOERI/HAZUS curves) | ~15,400 | 53,537 |
| USGS empirical model calibrated for Türkiye | ~21,300 | |
| This project, calibrated to Istanbul earthquakes | ~2,200 | |
| This project, calibrated to all four earthquakes | ~24,700 | |

Even the best version overestimated 1999 Istanbul by about 3× and underestimated 6 February by about 2×, and it assigned far more of
the deaths to masonry buildings than actually happened. Fixing this takes real damage data broken down by building type and floor count,
not parameter tuning (the Ministry inspected 2.15 million buildings one by one; this data is not openly available in bulk).

That all methods underestimate losses in large, long-duration earthquakes is a known difficulty in the literature too.

**Decision:** No death count is published for Istanbul. The damage model is used only for rough magnitudes (how many people in which
neighbourhood live in damaged buildings); the assembly calculation rests mainly on population and area.

Code: \`model/hs_*\`, \`sinama/\`, document: \`docs/YONTEM_2_HASAR.md\`.

---

## 5. Assembly: an optimisation problem

**What:** On the night of an earthquake, is there space within walking distance for everyone who goes outside?

**Why a simple ratio is not enough:** "Park area in the neighbourhood ÷ population" is misleading: one park serves several
neighbourhoods, and people only go where they can walk.

**Toy example:** Picture three streets (A, B, C; 100 people each) and two parks: P1 holds 100 people, P2 holds 250. Total capacity is
350 and there are 300 people, so on paper there is room for everyone. But A and B can only walk to P1, and P2 is only near C. The 200
people of A and B do not fit into P1's 100 places: **100 people find no space**, while 150 places sit empty in P2. The total says
"enough"; the location says "not enough".

**How (at full scale):**
- Istanbul was divided into ~49,000 blocks (squares of about 250 m); each block's population was distributed by building volume.
- 2,960 open spaces over 2,000 m² are candidates (the same order of magnitude as the 3,021 areas announced by AFAD). The usable share
  of each depends on its type: pitches and squares 90%, parks 60%, school grounds 50%, groves and forest 20%. 1.5 m² per person.
- Each block is assigned to open spaces within 1 km walking distance; no space can exceed its capacity. The goal is first to find space
  for as many people as possible, then to minimise total walking. This is a "transportation problem"; the linear program has about
  170,000 variables and solves in half a second.
- How many people go outside: those living in damaged buildings plus a fear share that rises with shaking (10% at 0.05 g, 80% at 0.30 g).

**What came out:** In the median earthquake, **2.7 million** of the 9.1 million people outside on the first night find no space within
1 km.

| If the assumption changes | No space |
|---|---|
| 2 m² per person | 3.4 million |
| Walking limit 1.5 km | 1.6 million |
| Half as many people go outside | 0.85 million |
| Everyone goes outside | 6.4 million |

**Limits:** "How many people go outside" is the assumption that matters most; that is why a range is given. The open-space layer is not
the official list.

Code: \`ihtiyac/i01–i02\`, document: \`docs/YONTEM_5_IHTIYAC.md\`.

---

## 6. Machine learning: where we used it and where we gave up

**a) Building height (used on the site).** Only 4% of the buildings on the 3D map have a known height. We trained a model (LightGBM) on
72,000 Istanbul buildings with a known floor count. For each building it looks at footprint area and shape, the surrounding buildings,
the average height measured from satellite and the neighbourhood's İBB floor distribution. It was tested on districts it never saw: it
gets the floor class (1–4 / 5–8 / 9+) right 67% of the time, against 59% for a simple rule. It still underestimates tall buildings;
heights on the map are marked as "estimated".

**b) Understanding the open scenario data.** We built a model that explains the neighbourhood damage rates published by İBB and looked at
which information weighs most (SHAP). Result: distance to the fault dominates the scenario's damage pattern by far, followed by the share
of pre-1980 buildings and the share of buildings over 5 floors. On districts it never saw, our physics-based calculation explains 50% of
the variance, and 59% together with machine learning; a randomly split test inflates this by about 0.1, which is why district hold-out
testing was used.

**c) An attempt we dropped: learning from 6 February.** We tried to build a "which building collapsed under how much shaking" model
from 47,000 building damage labels that the European Copernicus service marked on satellite images. In regions it never saw, the model
separated collapsed buildings only slightly better than a coin flip (AUC 0.54–0.68). The reason was the labels: each region was marked
on a different date with different imagery. This attempt was left out of the results.

**d) A fast surrogate of the simulator.** We built a model (R² 0.96) that imitates the 72-hour simulator and runs instantly in the
browser; once the simulator left the main story, this model was no longer used on the site.

Code: \`ml/\`, document: \`docs/YONTEM_4_ML.md\`.

---

## 7. The 72-hour simulator: how it works, and why it is not in the main story

**What:** A model that plays out the 72 hours after the earthquake in 15-minute steps: the falling survival chances of people trapped
under rubble, teams moving between neighbourhoods on a damaged road network, bridge and debris closures, hospitals filling up.

**How:** Victims are tracked as pools per neighbourhood and teams as individual agents. The survival curve comes from rescue data of past
earthquakes (Coburn et al. 1992); bridge damage from HAZUS curves. Four team dispatch rules and one optimised plan were compared on the
same random earthquakes; field hospital locations were optimised separately.

**Why it is not in the main story:** The simulator's input is who is trapped under rubble. That comes from the damage model that failed
the 6 February test. The mechanisms (e.g. rescue slowed by crowds) are sound, but the absolute numbers are not reliable enough.

Code: \`sim/\`, document: \`docs/YONTEM_3_SIMULASYON.md\`.

---

## 8. Esenyurt figures

| Item | Value | How |
|---|---|---|
| Walkable street space (Turgut Özal) | ~84,000 m² | OSM road length × width by road type, minus cars parked overnight |
| Vehicles (Esenyurt) | 150–240k | TÜİK Istanbul: 241 cars per 1,000 people; lower bound 150 |
| District exit capacity | ~68,000 vehicles/hour | Lanes × per-lane capacity of motorways, primary and secondary roads crossing the boundary |
| Hospital beds | ~720 (0.7 per 1,000) | Provincial bed total distributed by the building area of hospital campuses |
| Camp area needed (Turgut Özal) | 346,050 m² | İBB's shelter need of 7,690 people × 45 m² per person (Sphere) |

---

## 9. Maps

The basemap comes from OpenStreetMap data (Protomaps build, October 2026) and is served from within the site as a single file. Buildings
are Overture footprints; their heights come from the model in section 6 (the real value where it is known). The assembly flows are the
direct output of the optimisation in section 5.

---

## 10. Limitations and honesty notes

- This is an independent portfolio study; it does not forecast earthquakes and does not evaluate the plans or work of official
  institutions.
- The assembly result is not an evaluation of the official assembly area plan; it uses potential areas derived from open data.
- No death count is published (section 4).
- The assembly result depends most on the "how many people go outside" assumption; a range is given.
- The data comes from different years: population 2025, open spaces and roads 2026, while building age and floor classes and the İBB
  earthquake scenario rest on the 2017 building stock. That is why age and floor shares are given "in the 2017 census", people per
  building is given as a range using both the 2017 census and current footprints, and the shelter need is treated as a lower bound. The
  assembly calculation uses only 2025 population and current open spaces; it does not rely on the old building data.
- Soil data is coarse; hospital beds are an estimate distributed from the provincial total.
- Errors we found in our own calculations along the way (e.g. a ratio computed with the wrong population) were corrected and noted in the
  documents.

## Reproducing

All code and the order of steps are in the repository (\`docs/ILERLEME.md\`). Raw data is downloaded with \`scripts/00_indir.py\`; the
pipeline runs with a single command.
`,q=t(),J=n[q],Y=q===`tr`?`en`:`tr`;document.title=J.baslikNasil,document.getElementById(`ust-bar`).innerHTML=`<a href="./?lang=${q}" class="marka geri">${J.hikayeyeDon}</a><nav class="ust-baglar"><a href="${e(Y)}" class="dil" hreflang="${Y}" aria-label="${J.oburDilAd}">${J.oburDil}</a><span class="bag etkin" aria-current="page">${J.nasilYaptik}</span></nav>`,document.getElementById(`icindekiler-baslik`).textContent=J.icindekiler,document.querySelector(`.icindekiler`).setAttribute(`aria-label`,J.icindekiler);var je=q===`tr`?ke:Ae,X=document.getElementById(`nasil`),Z=document.getElementById(`icindekiler`),Me=je.replace(/^# .*\n+/,``).replace(/^(>.*\n)+/m,``);X.innerHTML=`<p class="ust">${J.yontem}</p><h1>${J.nasilYaptik}</h1>
  <p class="spot">${J.spot}</p>
  ${K.parse(Me,{async:!1})}`,X.querySelectorAll(`table`).forEach(e=>{let t=document.createElement(`div`);t.className=`tablo`,t.tabIndex=0,e.replaceWith(t),t.appendChild(e)});var Ne=e=>e.toLocaleLowerCase(`tr`).normalize(`NFD`).replace(/[̀-ͯ]/g,``).replace(/ı/g,`i`).replace(/[^a-z0-9]+/g,`-`).replace(/^-|-$/g,``),Q=[...X.querySelectorAll(`h2`)];Q.forEach(e=>{e.id=Ne(e.textContent??``)}),Z.innerHTML=Q.map(e=>`<li><a href="#${e.id}">${e.textContent}</a></li>`).join(``);var Pe=new IntersectionObserver(e=>{for(let t of e)t.isIntersecting&&Z.querySelectorAll(`a`).forEach(e=>e.classList.toggle(`aktif`,e.getAttribute(`href`)===`#${t.target.id}`))},{rootMargin:`0px 0px -70% 0px`});Q.forEach(e=>Pe.observe(e));var Fe=document.getElementById(`icindekiler-kutu`),$=window.matchMedia(`(min-width: 60.01rem)`),Ie=()=>{Fe.open=$.matches};Ie(),$.addEventListener(`change`,Ie),Z.addEventListener(`click`,e=>{!$.matches&&e.target.tagName===`A`&&(Fe.open=!1)});