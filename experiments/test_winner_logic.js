function determineWinner(score) {
    if (!score) return null

    // Remove retirements/walkovers for parsing
    const cleanScore = score.replace(/\s*\(RET\)|\s*\(W\/O\)/i, '').trim()
    const sets = cleanScore.split(' ')

    let p1Sets = 0
    let p2Sets = 0

    sets.forEach(set => {
        // Handle super tiebreaks or normal sets
        if (set.includes('-')) {
            const [g1, g2] = set.split('-').map(v => parseInt(v))
            if (!isNaN(g1) && !isNaN(g2)) {
                if (g1 > g2) p1Sets++
                else if (g2 > g1) p2Sets++
            }
        }
    })

    if (p1Sets > p2Sets) return 'player1'
    if (p2Sets > p1Sets) return 'player2'
    return null // Draw or incomplete
}

const testCases = [
    { score: "6-4 6-4", expected: "player1" },
    { score: "4-6 6-4 6-0", expected: "player1" },
    { score: "6-7 6-7", expected: "player2" },
    { score: "6-0 0-6 10-8", expected: "player1" }, // Super tiebreak
    { score: "6-4 2-0 (RET)", expected: "player1" },
    { score: "0-0 (RET)", expected: null }, // Tie/Incomplete
]

let passed = 0
testCases.forEach(t => {
    const result = determineWinner(t.score)
    if (result === t.expected) {
        console.log(`PASS: ${t.score} -> ${result}`)
        passed++
    } else {
        console.error(`FAIL: ${t.score} -> expected ${t.expected}, got ${result}`)
    }
})

if (passed === testCases.length) console.log("All tests passed!")
else console.log(`${passed}/${testCases.length} tests passed.`)
