"""Simple boolean search parser/evaluator for include/exclude text queries."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


def _tokenize(expr: str) -> List[str]:
    """Split expression into tokens preserving quoted phrases and parentheses."""
    tokens: List[str] = []
    buf: List[str] = []
    in_quote = False
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == '"':
            if in_quote:
                # End quote.
                tokens.append("".join(buf).strip())
                buf.clear()
                in_quote = False
            else:
                if buf:
                    tokens.append("".join(buf).strip())
                    buf.clear()
                in_quote = True
        elif ch in "()":
            if in_quote:
                buf.append(ch)
            else:
                if buf:
                    tokens.append("".join(buf).strip())
                    buf.clear()
                tokens.append(ch)
        elif ch.isspace() and not in_quote:
            if buf:
                tokens.append("".join(buf).strip())
                buf.clear()
        else:
            buf.append(ch)
        i += 1
    if buf:
        tokens.append("".join(buf).strip())
    return [t for t in tokens if t]


def _to_postfix(tokens: Sequence[str]) -> List[str]:
    """Convert tokens to postfix (shunting-yard) supporting AND/OR."""
    prec = {"AND": 2, "OR": 1}
    output: List[str] = []
    stack: List[str] = []
    for tok in tokens:
        if tok in ("AND", "OR"):
            while stack and stack[-1] in prec and prec[stack[-1]] >= prec[tok]:
                output.append(stack.pop())
            stack.append(tok)
        elif tok == "(":
            stack.append(tok)
        elif tok == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if stack and stack[-1] == "(":
                stack.pop()
        else:
            output.append(tok)
    while stack:
        output.append(stack.pop())
    return output


def _match_token(token: str, haystack: str) -> bool:
    return token.lower() in haystack


def _eval_postfix(postfix: Sequence[str], haystack: str) -> bool:
    if not postfix:
        return True
    stack: List[bool] = []
    for tok in postfix:
        if tok == "AND":
            b = stack.pop() if stack else False
            a = stack.pop() if stack else False
            stack.append(a and b)
        elif tok == "OR":
            b = stack.pop() if stack else False
            a = stack.pop() if stack else False
            stack.append(a or b)
        else:
            stack.append(_match_token(tok, haystack))
    return stack[-1] if stack else False


def evaluate_expression(expr: str, haystack: str) -> bool:
    """Evaluate a logical expression (AND/OR/()/"") against haystack."""
    expr = expr.strip()
    if not expr:
        return True
    tokens = _tokenize(expr)
    # Treat lowercase "and"/"or" as literals; only uppercase becomes operators.
    tokens = ["AND" if t == "AND" else "OR" if t == "OR" else t for t in tokens]
    try:
        postfix = _to_postfix(tokens)
    except Exception:
        return False
    return _eval_postfix(postfix, haystack)


def _card_text(card: Dict[str, object]) -> str:
    text_bits: List[str] = []
    if "scanned_text" in card and isinstance(card["scanned_text"], str):
        text_bits.append(card["scanned_text"])
    if "file_path" in card and isinstance(card["file_path"], str):
        text_bits.append(Path(card["file_path"]).name)
    if "pdf_path" in card and isinstance(card["pdf_path"], str):
        text_bits.append(Path(card["pdf_path"]).name)
    return " ".join(text_bits).lower()


def filter_cards(
    cards: Iterable[Dict[str, object]], include_expr: str, exclude_expr: str
) -> List[Dict[str, object]]:
    include_expr = include_expr.strip()
    exclude_expr = exclude_expr.strip()
    filtered: List[Dict[str, object]] = []
    for card in cards:
        text = _card_text(card)
        if not evaluate_expression(include_expr, text):
            continue
        if exclude_expr and evaluate_expression(exclude_expr, text):
            continue
        filtered.append(card)
    return filtered
