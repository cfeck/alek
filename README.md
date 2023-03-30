# ALEK
Assembler Learning Environment for Kids

# Quick Start
    - install Python 3 and PyQt 5
    - run "alek.py" with Python
    - click the menu arrow in the upper-right corner
    - click menu "Demo 1: Hi"
    - click the "Exec" button until the processor is halted
    - the video output now displays "Hi"
    - click menu "Reset" to enable execution again

# Architecture

Memory
    - is organized in 10 pages x 10 rows x 10 cells = 1000 cells
    - select page with the Memory tabs

Pages
    0..4    code or data
    5..6    (reserved for shared pages)
    7..8    mapped to the video output
    9       (reserved for the stack page)

Cells
    - contain a 3-digit decimal number (0..999, no hex/binary needed)
    - each cell has an address, also in range 0..999
    - double-click a cell to edit it via keyboard
    - click on the Code table entries to enter/edit instructions
    - drag-select multiple cells for menu "Clear Memory Cells"

CPU
    - 4 general registers named R1..R4
    - IP register (Instruction Pointer) has the address of the next instruction
    - ALU can perform ADDitions, SUBtractions, and CoMParisons with numbers
    - CMP result can be one of "less than (<)", "equal to (=)" , or "greater than (>)"
    - data flow is not yet visualized during execution

Codes for CPU Instructions
    (See the table in the "Code" tab)
    1ds     ADD to destination d the source s
    2ds     SUBtract from destination d the source s
    5ds     MOVe to destination d the source s
    6ds     CoMPare numbers from sources d and s
    7cs     JuMP if condition c is satisfied to cell s
    999     HaLT the processor

Addressing
    ###         number immediately after the code (only for source)
    R1..R4      number in register
    (R1)..(R4)  number in memory addressed by register
    (##)        number in memory with absolute address

Condition Codes
    1       <
    2       =
    4       >
    add codes for combinations, e.g. ">=" is 6

Code for Characters
    (See the table in the "Char" tab)
    5       space
    6..9    elementary punctation
    10..29  symbols/punctation
    30..39  0..9 digits
    41..66  A..Z letters
    71..96  a..z letters
