/**
 * TF-IDF retriever — a faithful TypeScript port of rag/retriever.py.
 *
 * Same algorithm, same parameters, so the same query returns the same
 * ranking as the Python pipeline:
 *   - tokenize: lowercase [a-z0-9]+ tokens, drop tokens of length <= 2
 *   - IDF: smoothed, log((n + 1) / (df + 1)) + 1
 *   - score: TF-IDF cosine similarity in [0, 1]
 */

const TOKEN_RE = /[a-z0-9]+/g;

export function tokenize(text: string): string[] {
  return (text.toLowerCase().match(TOKEN_RE) ?? []).filter((t) => t.length > 2);
}

function counter(tokens: string[]): Map<string, number> {
  const map = new Map<string, number>();
  for (const t of tokens) map.set(t, (map.get(t) ?? 0) + 1);
  return map;
}

export class TfidfRetriever {
  private readonly docIds: string[];
  private readonly tf: Map<string, number>[];
  private readonly idf = new Map<string, number>();
  private readonly norms: number[];

  constructor(documents: Record<string, string>) {
    this.docIds = Object.keys(documents);
    this.tf = this.docIds.map((d) => counter(tokenize(documents[d])));

    const df = new Map<string, number>();
    for (const tf of this.tf) {
      for (const term of tf.keys()) df.set(term, (df.get(term) ?? 0) + 1);
    }
    const n = this.docIds.length;
    for (const [term, c] of df) {
      this.idf.set(term, Math.log((n + 1) / (c + 1)) + 1.0);
    }
    this.norms = this.tf.map((tf) => {
      let sum = 0;
      for (const [t, count] of tf) sum += (count * (this.idf.get(t) ?? 0)) ** 2;
      return Math.sqrt(sum) || 1.0;
    });
  }

  private vector(tokens: string[]): Map<string, number> {
    const tf = counter(tokens);
    const vec = new Map<string, number>();
    for (const [t, count] of tf) {
      const idf = this.idf.get(t);
      if (idf !== undefined) vec.set(t, count * idf);
    }
    return vec;
  }

  /** Return [chunkId, score] pairs for the top-k chunks, best first. */
  retrieve(query: string, topK = 2): Array<[string, number]> {
    const qv = this.vector(tokenize(query));
    let qNormSq = 0;
    for (const v of qv.values()) qNormSq += v * v;
    const qnorm = Math.sqrt(qNormSq) || 1.0;

    const scored: Array<[string, number]> = this.docIds.map((docId, i) => {
      const tf = this.tf[i];
      let dot = 0;
      for (const [t, qWeight] of qv) {
        const count = tf.get(t);
        if (count !== undefined) dot += qWeight * count * (this.idf.get(t) ?? 0);
      }
      return [docId, dot / (qnorm * this.norms[i])] as [string, number];
    });
    // Array.prototype.sort is stable, matching Python's sort on ties.
    scored.sort((a, b) => b[1] - a[1]);
    return scored.slice(0, topK);
  }
}
