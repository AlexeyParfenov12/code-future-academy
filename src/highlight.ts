import {createHighlighterCore} from 'shiki/core';
import {createJavaScriptRegexEngine} from 'shiki/engine/javascript';
import python from 'shiki/langs/python.mjs';
import dark from 'shiki/themes/github-dark.mjs';
const highlighter=createHighlighterCore({langs:[python],themes:[dark],engine:createJavaScriptRegexEngine()});
export async function highlight(code:string){return (await highlighter).codeToTokens(code,{lang:'python',theme:'github-dark'}).tokens}
