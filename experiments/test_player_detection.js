const matches = [
    { info: { player1_name: 'Marcolino', player2_name: 'Federer', score: '6-4 6-4' }, player1: {}, player2: {} },
    { info: { player1_name: 'Nadal', player2_name: 'Marcolino', score: '6-3 6-3' }, player1: {}, player2: {} },
    { info: { player1_name: 'Marcolino', player2_name: 'Djokovic', score: '7-6 7-6' }, player1: {}, player2: {} },
    { info: { player1_name: 'Murray', player2_name: 'Marcolino', score: '6-1 6-1' }, player1: {}, player2: {} },
]

// 1. Detect Main Player
const names = {}
matches.forEach(m => {
    if (m.info) {
        names[m.info.player1_name] = (names[m.info.player1_name] || 0) + 1
        names[m.info.player2_name] = (names[m.info.player2_name] || 0) + 1
    }
})
const mainPlayer = Object.keys(names).reduce((a, b) => names[a] > names[b] ? a : b)

if (mainPlayer === 'Marcolino') {
    console.log("PASS: Main Player detected correctly as Marcolino")
} else {
    console.error("FAIL: Main Player detected as " + mainPlayer)
}

// 2. Available Opponents
const opponents = new Set()
matches.forEach(m => {
    if (m.info) {
        if (m.info.player1_name !== mainPlayer) opponents.add(m.info.player1_name)
        if (m.info.player2_name !== mainPlayer) opponents.add(m.info.player2_name)
    }
})
const oppList = Array.from(opponents).sort()

if (oppList.length === 4 && oppList.includes('Federer') && oppList.includes('Nadal')) {
    console.log("PASS: Opponents list correct: " + oppList.join(', '))
} else {
    console.error("FAIL: Opponents list incorrect: " + oppList.join(', '))
}
