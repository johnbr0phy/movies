# BARNEY: the long-form brief

*Written by Claude after the film was made, at John's request, in the style of The Bicycle's brief. The film itself was made from the one-paragraph prompt quoted on the film page, not from this.*

I want you to independently make a complete short animated film, end to end. It's called "Barney." There is no script yet, no storyboard, no design, no music and no sound. You're going to make all of it, start to finish. I'm not going to be here to answer questions, so make reasonable assumptions, write them down in a DECISIONS.md as you go, and keep moving.

At the highest level: Barney is a little boy, about seven, walking through a world that deforms and confuses us. The film should be mind-bending. It should confuse the watcher with strange perspectives and illusions, and every step of the way we should think we know what's coming, and it should never turn out the way we thought it would. I want it to feel incredibly stylised and artistic, the kind of short that wins something at Cannes and makes a room go quiet for a second before people clap. It should not feel like a tech demo of optical illusions. It needs a heart.

Some things have to happen. A door opens, and on the other side is a flat plane at a completely different horizontal angle, a floor that is someone else's wall, and he steps through onto it as if nothing were odd. He walks up a wall. He slides up a slide. Everything else is yours to invent, and I want you to invent more than I've listed. Staircases, corridors, crowds, cities, skies, water. Push it.

Here is the most important piece of direction I can give you: confusion without rules is just noise. A film of random surreal images wears an audience out in about a minute. Decide on a small set of rules for how this world bends, make them simple enough that an audience learns them without being told, and then spend the whole film using those rules to surprise them. Give the viewer something to hold on to, a compass, something in every shot that always tells the truth even when the picture is lying, so that they can feel themselves being fooled. Then, near the end, take the compass away or turn it inside out. The best surprises should be obvious in hindsight.

Barney should be carrying something. Something small and fragile, maybe alive, that he is trying to get somewhere, so that the walk has stakes and the illusions put something at risk. Decide what it is and why it matters, and reveal that slowly rather than explaining it up front. Decide where he's going and whether he gets there. I don't want the ending to be "it was all a dream." That cancels a film instead of finishing it. I want the last turn to be emotional, not just geometric: the final illusion should change what the whole film meant.

Visually, think Jean Paul Gaultier, Issey Miyake and The Fifth Element. I don't mean costumes from those designers or shots from that film. Don't copy any garment, logo, character or frame. Take the sensibilities and turn them into rules:

- the Breton stripe, the cone and the couture tailoring of Gaultier;
- the permanent pleat and the flat, folded, geometric garments of Miyake;
- the vertical city, the layered flying traffic, the tangerine-and-teal palette and the Franco-Belgian comic-book lineage of The Fifth Element.

I want a strong, coherent graphic style of your own that sits in that world: flat colour, confident clean linework, real design in every frame. Stripes and pleats are useful for more than decoration. Ruled lines show you exactly how space is bending, so use pattern as a way of drawing perspective. Pick a palette for each part of the story and make the changes between them mean something. If colour leaves the film at some point, the audience should feel it go.

Think about your capabilities and be realistic. If you have image and video models available, read their documentation before you generate anything. If you don't, and honestly even if you do, consider building the film as real 3D in code, because this story needs rolling horizons, walls that become floors, cameras that orbit things that aren't what they seem, and perspective tricks that only work from one exact angle. Whatever you use, the finished frames should look drawn and designed, not rendered. Write your own shaders if you have to. Ink lines, flat shading, paper, pattern.

Be rigorous about planning before you make anything. The most common failure here is that the pieces don't cohere: colours drift between shots, the boy's proportions change, the illusions stop obeying their own rules, the music hits the wrong moment, and it all feels jarring.

1. Do the thought work first. Write the story beat by beat.
2. Write a shot list. Every shot gets a number, a duration, a description, a camera move, which characters are in it, what emotional beat it carries, and what the audio is doing. Do not generate anything without a shot list.
3. Make a real style sheet: palettes by act, surface patterns, line weight, how shadow falls, and a "do not do this" section.
4. Make character sheets for Barney: a turnaround (front, three-quarter, side, back), a range of poses, and his expressions. Do the same for whatever he's carrying and for anyone he meets. Barney must be the same boy from every angle and at every roll of the camera. If he drifts, fix it before you move on.

Camera. Illusions only work from the right place, so think carefully about where the camera stands in every shot and why. Use orthographic views where a trick needs them. Use the roll of the camera as a storytelling device: sometimes it agrees with Barney about which way is down, sometimes it disagrees, and sometimes it changes its mind a beat late. Use stillness. A locked-off symmetrical frame with one impossible thing happening in it is worth more than a spinning camera. Mostly hold the camera still and let the world move.

Animation. Barney's walk matters. He should walk the same way whatever he's walking on, at a steady pace, completely untroubled, because his calm is funny and it's what makes the world's strangeness land. Give the world a different kind of motion from the boy. If you animate him at twelve drawings a second while the camera moves at twenty-four, he'll feel drawn and the world will feel filmed, and that contrast is worth having. Anything the world does to him, he accepts.

There's no dialogue in this film. No spoken words at all. Barney can gasp and giggle. The world can creak, whoosh, drip and hum. The score and sound design do the emotional heavy lifting, so take them seriously. I want an original score, timed to picture.

- Write a small, memorable motif that could be whistled, and let the music bend the way the world bends. Turn it upside down when the world turns over. Play it backwards when time or direction goes backwards. Hold back the full statement until it counts.
- Consider putting the music against Barney's footsteps, so that he keeps a steady beat while the music limps around him.
- Use sound illusions too. A scale that rises forever. A slide that sounds as if it's playing backwards. Drips that fall the wrong way and rise in pitch.
- Use real sampled instruments where you can, synthesise what you can't, and choose instruments that belong to this world: harpsichord, marimba, glass, organ, something French and strange for the melody.
- Put every footstep on the frame where a foot lands.
- Know when to stop the music entirely.

Text on screen should be rare and beautiful: a title card in a Didone typeface with a little of the film's own trickery in it, and credits. No chapter cards, no subtitles. It should feel like one continuous walk.

Pacing. This is going to be posted on X, so the first five seconds have to make someone stop scrolling, and the whole thing should run between three and four minutes. Open on something with an immediate hook that is already quietly wrong. Build in acts:

- a playful discovery of the rules;
- an escalating run through stranger and stranger places;
- a loss, where the thing he's carrying is hurt and the world goes grey and quiet;
- a turn, where the rules themselves flip;
- an arrival;
- a final reveal that recontextualises everything.

Study how great short films and anime openings earn attention without shouting, and how Japanese and French animators use stillness.

Verify everything. After you build each shot, render a handful of frames, look at them, and ask honestly:

- Is Barney on model?
- Does the illusion actually read from this camera?
- Does every illusion obey the rules you set?
- Is anything clipping, floating, hidden behind something, or cut off by the frame?

Fix what's wrong and look again. Keep a production log of what broke and how you fixed it, so you stop repeating mistakes. When it's all rendered, cut the whole film together, watch it end to end, take a frame from every shot, and ask whether each one is up to the bar. Check the audio sync. Check that the palette of each act holds. Redo what isn't good enough, and watch it again.

You are far more capable than you think you are. You are a writer, a production designer, a director, an animator, a composer and a sound designer, all at once. Have that mindset the whole way through. The goal is a short film that makes people feel something unexpected on an ordinary afternoon. The stretch goal is something people pass around because they can't quite believe how it was made.

Deliverables:

- the final MP4 at 1080p with embedded audio;
- a 4:5 vertical cut for X;
- the style sheet and character sheets as PNGs;
- the beat sheet and shot list;
- DECISIONS.md;
- a short WRITEUP.md explaining what you made and why, in your own voice;
- a simple web page that presents the film, some stills and the sheets.

Make no mistakes.
