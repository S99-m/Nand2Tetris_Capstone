// Box.asm - Nand to Tetris Capstone, Part C
// Roll No: 2501730361   K = 61
// Box: starts at row 61 (K), 20 rows tall, 32 pixels wide (2 words) from the left edge.
// While any key is pressed the box is black; when released it is white (disappears).
//
// Screen facts: SCREEN = 16384, one row = 32 words, one word = 16 pixels.
// Row r starts at address SCREEN + 32*r.  Row 61 -> 16384 + 32*61 = 16384 + 1952 = 18336.

// ---------- INIT (runs once): box_start = SCREEN + 32 * START_ROW ----------
   @SCREEN
   D=A
   @box_start
   M=D              // box_start = 16384
   @61              // <<< START ROW (K = 61): change this ONE number to move the box up/down
   D=A
   @skip
   M=D              // skip = number of rows to move down from the top of the screen
(CALC_START)
   @skip
   D=M
   @INIT_DONE
   D;JEQ            // no rows left to skip -> box_start is ready
   @32
   D=A
   @box_start
   M=D+M            // one screen row down = +32 words
   @skip
   M=M-1
   @CALC_START
   0;JMP
(INIT_DONE)         // box_start is now 16384 + 61*32 = 18336

// ---------- MAIN LOOP: poll keyboard, choose colour, draw ----------
(MAIN_LOOP)
   @KBD
   D=M
   @SET_BLACK
   D;JNE            // any key pressed (KBD != 0) -> black
   @color
   M=0              // no key -> white (0000000000000000)
   @DRAW_START
   0;JMP
(SET_BLACK)
   @color
   M=-1             // key pressed -> black (1111111111111111)

// ---------- DRAW: one shared loop, colour comes from @color ----------
(DRAW_START)
   @box_start
   D=M
   @addr
   M=D              // addr = first word of the first box row
   @20              // <<< HEIGHT in rows: change this ONE number to resize the box height
   D=A
   @rows
   M=D              // rows = rows still to draw
(ROW_LOOP)
   @color
   D=M              // D = -1 (black) or 0 (white)
   @addr
   A=M              // A = address of word 0 of this row
   M=D              // pixels 0..15  of the row
   A=A+1            // next word to the right (addr + 1)
   M=D              // pixels 16..31 of the row  (2 words = 32 pixels wide)
                    // WIDER box: add another "A=A+1" and "M=D" pair here (+16 pixels each)
   @32
   D=A
   @addr
   M=D+M            // addr += 32  -> same word, one row further down
   @rows
   M=M-1            // one row finished
   D=M
   @ROW_LOOP
   D;JGT            // rows > 0 -> draw next row
   @MAIN_LOOP
   0;JMP            // done -> poll the keyboard again
