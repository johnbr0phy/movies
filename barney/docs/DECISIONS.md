# DECISIONS

Assumptions and choices for *BARNEY*, in the order they were made.

## 1. Brief

- **The request:** "a mind-bending short about a little boy called Barney, walking through a world that deforms and confuses us. Every step we think we know what's coming, but it never ends up that way. Doors open to a flat plane at a different angle. He walks up a wall and slides up a slide. Stylised and artistic. Think Jean Paul Gaultier, Issey Miyake and *The Fifth Element*. Something that could win at Cannes."
- **Assumption:** make the whole film end to end: story, design, animation, score, sound, the final cut, a vertical cut and the documentation, the same way *The Bicycle* was made.
- **Length:** about 3 minutes 30 seconds, which is within the usual festival short-film window and still watchable on X.
- **No dialogue.** Barney can gasp, giggle and hum. The world makes sounds. There are no words apart from the title and the credits.

## 2. Story

- **The confusions need a grammar, or they are noise.** A film of random surreal images tires an audience fast. So there are two gravities (see docs/STORY.md): Barney's local down, and the true down that only the water in the bag obeys. The audience learns to read the water line, and the film keeps finding new ways to overturn what they have learned.
- **An object carried with care gives the walk stakes.** A goldfish in a bag is fragile, alive, and orange against a world of navy, white and grey. The bag leaking gives the middle of the film a clock.
- **The last reversal is emotional, not geometric.** Barney frees the fish into a sea that was the sky. Then the camera pulls back to show his whole world is a bowl on the sea floor, and the fish looks in at him. The boy who carried the fish was being kept by it.
- **I rejected "it was all a dream".** It cancels the film instead of completing it.

## 3. Look: Gaultier, Miyake, *The Fifth Element*

I didn't copy anything. I took three sensibilities and made rules from them.

- **Gaultier:** the Breton stripe (the marinière) as the base texture of the world, plus the cone and couture-style tailoring. Barney wears a navy and bone marinière.
- **Miyake:** permanent pleats and flat, folded, geometric garments. The Pleats are flat pleated paper people who vanish when seen edge on. The low point is a monochrome pleated plain.
- ***The Fifth Element*:** the vertical city, the layers of flying traffic, tangerine against teal, and the Franco-Belgian comics lineage behind it.
- **Line: ligne claire.** Even black outlines, flat colour, no gradients on characters, one hard shadow tone. That is the Franco-Belgian lineage that *The Fifth Element* came out of. The outlines come from a post-process that finds edges in depth, normals and object IDs, so every crease in the geometry is inked automatically and consistently.
- **Palettes by act:**
  - bone, navy and signal red (the corridor, door and plaza)
  - Miyake brights on pale grey (the Pleats, stairs and slide)
  - sodium tangerine and teal haze (the city)
  - monochrome greys with only the fish in colour (the low point)
  - ultramarine with a thousand orange fish (the sea)
- **Barney:** big round head, black bob with a blunt fringe, dot eyes, a navy and bone marinière, a small bone-white pleated capelet, black shorts, white socks, and red T-bar shoes.
- **Camera:** mostly locked-off, symmetrical frames. Moves are slow and deliberate: rolls, orbits and one long pull-back. Isometric orthographic projection for the staircase, because the Penrose trick only works there. The hook opens on a close-up.
- **Frame rate:** the camera and the world move at 24 fps. Barney's body is posed at 12 drawings a second, so he reads as animated and the world reads as filmed.

## 4. Technique

- **Real 3D, stylised.** The film needs rolling horizons, walls that turn into floors and a camera that orbits flat people, so it is built as a 3D scene. The renderer is three.js running in headless Chromium through SwiftShader WebGL. A test frame rendered in about 6 ms.
- **Custom shaders for everything:**
  - flat toon colour with one shadow band
  - procedural stripes and pleats drawn in object space, so they wrap the form
  - an ID, normal and depth buffer for the outline pass
  - paper grain and a slight print feel in post
- **Water:** the bag has a fill volume. Each frame the water level is solved against the *true* down by sampling the bag's interior, and the water surface is drawn as the flat-coloured back faces of the clipped volume.
- **Characters are procedural rigs built from primitives.** That keeps Barney identical from every angle and under every roll.
- **Output:** each frame is read back from the canvas as a PNG and encoded per shot with ffmpeg.

## 5. Sound and score

- **Tempo:** Barney's steps are fixed at two a second, 120 steps a minute. The score is in 7/8 at a quarter note of 120, so the steps and the bar only line up every two bars. The music limps and Barney doesn't.
- **Instruments:**
  - a French harpsichord and marimba for the ostinato
  - a synthesised ondes Martenot for the melody (a French instrument, ribbon glides and all)
  - wine glasses as a glass harmonica for the fish and the bowl
  - a bowed psaltery for the shimmer
  - a pipe organ for the turn
  All the samples come from the VCSL CC0 library.
- **The motif turns with the world.** A five-note motif plays upside down (melodic inversion) every time the world flips, and backwards (retrograde) when Barney walks down stairs to go up. It is heard whole only at the release, right way up and inverted together as a mirror canon.
- **Illusions in sound:**
  - a Shepard scale for the endless stairs
  - reversed audio for sliding up the slide
  - drips that rise in pitch as they fall upwards
- **The music stops completely for the low point.**

## 6. Titles

- **Title:** BARNEY in a Didone (Bodoni Moda), with its letters striped like a marinière.
- **Credits** are on white paper at the end.
- **No chapter cards.** The film should flow like one continuous walk.

## 7. Production decisions

- **The renderer.** SwiftShader WebGL in headless Chromium. Frames take 2 to 10 s each, so supersampling was lowered from 2x to 1.5x, with the outline width scaled to match. The ligne-claire look didn't change.
- **Outlines.** The first depth-edge test drew false lines across receding floors. It now inks only where the second difference of inverse depth breaks: a plane is linear in 1/z, so a step (occlusion) is the only thing that fires.
- **Penrose stairs.** The first version, a closed ring with a shifted final run, didn't read. The stairs are now built for real as an open spiral of 20 steps whose top sits exactly one view vector (2.4, 2.4, 2.4) from its bottom.
- **The plaza floor.** A bug drew the chequer as stripes, so through the little door you saw one giant tilted tile instead of a floor on its side. Fixed to a true chequer, and S05 to S08 were re-rendered.
- **The reflection in the fish's eye.** A pale silhouette read as an abstract shape, so it's redrawn in Barney's own colours, upside down.
- **The touch (S23).** The fish was lost inside the tinted water column. The camera is now tighter and the column clearer.
- **Licensing.** The first mix borrowed a few ESC-50 recordings (CC BY-NC). Every one was replaced with synthesis, so the soundtrack is CC0 samples plus code.
- **Disk.** A render failed when the disk filled with intermediate PNGs. The renderer now deletes each shot's frames once it's encoded.

