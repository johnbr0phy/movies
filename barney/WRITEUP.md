# BARNEY

*A 3 minute 30 second animated short with no dialogue. Written, designed, animated and scored by Claude, from a single paragraph of direction.*

## The brief

> I want the movie to be kinda mind bending: it should confuse the watcher with stranger perspectives and illusions, it should feel incredibly stylized and artistic. Think Jean Paul Gaultier, Issey Miyake and The Fifth Element. It should be about a little boy called Barney, walking through a world that deforms and confuses us. Every step we think we know what's coming but it never ends up the way we thought it would. Doors open to a flat plane on a different horizontal angle. He walks up a wall and slides up a slide. It should be an interesting watch. Something that would win an award at Cannes.

## What I made

A small boy in a Breton top carries a goldfish in a plastic bag through a world that won't stay the right way up.

- He walks down a gallery that is really a funnel.
- He opens a knee-high door onto a plaza lying on its side, and steps out onto it.
- He walks up a wall and joins a runway of flat paper people who vanish when you see them edge on.
- He climbs a staircase that goes up forever and arrives where it started, then slides UP a slide into the sky.
- He lands on the face of a skyscraper and strolls down it like a pavement.
- A flying taxi nicks the bag. The colour drains out of the world, and the water starts dripping upward.
- He follows the drips until the horizon rolls over, and finds the sky was the sea.
- He lets the fish go. Then the camera pulls back, and his whole world is a glass bowl on the floor of a real sea, with the fish looking in at him.

## Rules for the confusion

A film of random surreal images tires an audience in a minute. So the illusions follow rules the audience can learn, and then the film overturns them.

1. **Barney's down is whatever he is standing on.** Walls, ceilings, the face of a tower. He never notices.
2. **The water in the bag always knows the true down.** It is the audience's compass. When the water line is sideways in the frame, the picture is lying to you.
3. **The camera takes Barney's side late,** rolling to agree with him a beat after he has already changed his mind about gravity.

Everything else is built to break expectations inside those rules:

- **The gallery (Borromini's Galleria Spada).** A 7 m corridor built to look like 30 m, so he grows as he walks away from us.
- **The stairs (Penrose's).** Built for real in 3D as an open spiral whose top sits exactly one view vector from its bottom. From the one magic angle they close; from anywhere else they are a drop, and he jumps it.
- **The runway.** The Pleats are single sheets of pleated paper, so the moment the camera swings edge-on they cease to exist.
- **The ending.** The final reversal is emotional, not geometric: the boy who spent the whole film carrying a fish was being carried by it.

## The look

I didn't copy any designer's work. I took three sensibilities and made rules from them:

- **Gaultier:** the marinière stripe as the texture of the world, and the cone.
- **Miyake:** permanent pleats, and flat folded garments that become people.
- **The Fifth Element:** a vertical city of flying traffic in tangerine and teal.

It is all drawn *ligne claire*: flat colour, one hard shadow band, and one even ink line found from depth, normals and object edges. That is the Franco-Belgian comics tradition the city scenes come from.

## How it was made

- **Picture.** A real 3D film rendered with three.js in headless Chromium through a software GPU, through my own shaders:
  - toon colour
  - stripes, chequers and pleats drawn in object space
  - an outline pass that inks planes cleanly using the Laplacian of inverse depth
  - paper grain

  Barney's body is posed at 12 drawings a second while the camera moves at 24. The water in the bag is solved every frame: the fill volume is sampled and the water surface is cut against the true down.
- **Characters.** Barney, the goldfish and the Pleats are all procedural, so they are identical from every angle and under every roll of the camera.
- **Score.**
  - Instruments: sampled French harpsichord, marimba, rubbed wine glasses, bowed psaltery, pipe organ, glockenspiel and strings (CC0 samples), plus a synthesised ondes Martenot with ribbon glides and a "palme" resonator.
  - Rhythm: the music is in 7/8 against Barney's steady two steps a second, so it limps and he doesn't.
  - Motif: a five-note motif turns upside down whenever the world does and runs backwards on the stairs. It is heard whole only once, right way up and upside down together as a mirror canon, when the fish goes home.
  - The endless stairs climb a Shepard scale that rises a semitone with every step.
  - Sliding up the slide, the sound plays backwards.
- **Sound.** All synthesised. Every footstep is placed from the same walk functions the shots use, so they land on the frame where each foot touches down.

## Honest limits

- The rigs are simple and procedural. Walks are cycles; nobody drew these poses by hand.
- The water is a flat-shaded surface, not a fluid simulation.
- Every sound is either a CC0 instrument sample or synthesised in code: footsteps, drips, pours, birds, traffic, the hinge of the door. There are no field recordings, so nothing in the soundtrack carries a non-commercial licence.
