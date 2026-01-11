// Mystical Purple and Pink Fire with Swirling Magical Flames
// Seamlessly looping over 1.5 seconds

#define PI 3.14159265359
#define TAU 6.28318530718
#define DURATION 1.5

// Hash function for randomness
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float hash1(float n) {
    return fract(sin(n) * 43758.5453);
}

// Smooth noise
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// Fractal Brownian Motion - looping version
float fbmLoop(vec2 p, float cycle) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    
    // Use sin/cos for cyclic animation
    vec2 timeOffset = vec2(sin(cycle), cos(cycle)) * 2.0;
    
    for(int i = 0; i < 6; i++) {
        value += amplitude * noise(p * frequency + timeOffset * float(i + 1) * 0.3);
        amplitude *= 0.5;
        frequency *= 2.0;
    }
    return value;
}

// Swirling distortion - perfectly cyclic
vec2 swirl(vec2 uv, vec2 center, float strength, float cycle) {
    vec2 delta = uv - center;
    float dist = length(delta);
    float angle = atan(delta.y, delta.x);
    angle += strength * exp(-dist * 2.5) * sin(cycle);
    return center + dist * vec2(cos(angle), sin(angle));
}

// Main fire shape with swirling flames
float fireShape(vec2 uv, float cycle, float timeLinear) {
    vec2 centered = uv - vec2(0.5, 0.2);
    
    // Taper the fire upward
    float taper = 1.0 - centered.y * 0.7;
    centered.x /= max(taper, 0.25);
    
    // Multiple swirl layers for complex motion
    vec2 swirled = swirl(uv, vec2(0.5, 0.35), 0.6, cycle);
    vec2 swirled2 = swirl(uv, vec2(0.45, 0.4), 0.4, cycle * 1.3 + 1.0);
    vec2 swirled3 = swirl(uv, vec2(0.55, 0.45), 0.3, -cycle * 0.7 + 2.0);
    
    // Fire base distance
    float dist = length(centered * vec2(1.0, 0.6));
    
    // Looping noise distortion
    float noiseOffset = fbmLoop(uv * 5.0, cycle) * 0.35;
    noiseOffset += fbmLoop(swirled * 7.0, cycle * 1.5) * 0.2;
    noiseOffset += fbmLoop(swirled2 * 3.0, -cycle * 0.8) * 0.15;
    
    // Flame tongues reaching upward
    float tongues = 0.0;
    for(int i = 0; i < 4; i++) {
        float fi = float(i);
        float phase = fi * 1.57 + cycle;
        float xPos = 0.35 + fi * 0.1 + sin(phase) * 0.08;
        float tongueHeight = 0.4 + sin(cycle + fi * 2.0) * 0.15;
        float tongue = smoothstep(0.08, 0.0, abs(uv.x - xPos)) * 
                       smoothstep(tongueHeight, 0.2, uv.y) * 
                       smoothstep(0.15, 0.25, uv.y);
        tongues += tongue * 0.3;
    }
    
    float flameBase = smoothstep(0.55 + noiseOffset, 0.05, dist);
    flameBase *= smoothstep(0.0, 0.18, uv.y); // Fade at bottom
    flameBase *= smoothstep(0.85, 0.6, uv.y); // Fade at top
    
    return clamp(flameBase + tongues, 0.0, 1.0);
}

// Inner hot core
float fireCore(vec2 uv, float cycle) {
    vec2 centered = uv - vec2(0.5, 0.28);
    centered.x *= 1.3;
    
    float dist = length(centered);
    
    // Pulsing core
    float pulse = 0.12 + sin(cycle * 2.0) * 0.02;
    float core = smoothstep(pulse + 0.05, pulse - 0.02, dist);
    
    // Add some noise variation
    core *= 0.8 + fbmLoop(uv * 8.0, cycle) * 0.4;
    
    return core * smoothstep(0.1, 0.2, uv.y);
}

// Ethereal wisps rising upward
float wisps(vec2 uv, float cycle, float linearTime) {
    float wispValue = 0.0;
    
    for(int i = 0; i < 7; i++) {
        float fi = float(i);
        float seed = hash1(fi * 123.456);
        float seed2 = hash1(fi * 789.012);
        
        // Cyclic vertical movement using fract
        float yPhase = fract(linearTime / DURATION + seed);
        float xWobble = sin(cycle + fi * 1.1) * 0.12 + sin(cycle * 2.0 + fi) * 0.05;
        
        vec2 wispPos = vec2(
            0.3 + seed2 * 0.4 + xWobble,
            0.2 + yPhase * 0.55
        );
        
        // Elongated wisp shape
        vec2 delta = (uv - wispPos) * vec2(1.5, 3.0);
        float dist = length(delta);
        
        // Fade out as it rises
        float fade = (1.0 - yPhase) * smoothstep(0.0, 0.1, yPhase);
        float wisp = smoothstep(0.12, 0.0, dist) * fade * 0.4;
        
        wispValue += wisp;
    }
    
    return wispValue;
}

// Glowing particles floating around
float particles(vec2 uv, float cycle, float linearTime) {
    float particleValue = 0.0;
    
    for(int i = 0; i < 25; i++) {
        float fi = float(i);
        float seed = hash1(fi * 12.34);
        float seed2 = hash1(fi * 56.78);
        float seed3 = hash1(fi * 90.12);
        
        // Cyclic orbital movement
        float angle = cycle + seed * TAU;
        float radius = 0.08 + seed2 * 0.2;
        
        // Rising motion with cycle
        float yBase = fract(linearTime / DURATION + seed);
        float xBase = 0.25 + seed2 * 0.5;
        
        vec2 particlePos = vec2(
            xBase + sin(angle) * radius * 0.4 + cos(angle * 0.7) * 0.05,
            0.12 + yBase * 0.6 + sin(angle * 0.5) * 0.04
        );
        
        float dist = length(uv - particlePos);
        float size = 0.006 + seed3 * 0.01;
        
        // Soft glow
        float glow = smoothstep(size * 4.0, 0.0, dist);
        
        // Twinkle effect - perfectly cyclic
        float twinkle = 0.4 + 0.6 * sin(cycle * 3.0 + seed * 20.0);
        
        // Fade based on height
        float fade = (1.0 - yBase * 0.6) * smoothstep(0.0, 0.15, yBase);
        
        particleValue += glow * twinkle * fade * 0.35;
    }
    
    return particleValue;
}

// Outer magical glow
float magicalGlow(vec2 uv, float cycle) {
    vec2 centered = uv - vec2(0.5, 0.35);
    centered.x *= 0.8;
    float dist = length(centered);
    
    float glow = smoothstep(0.5, 0.1, dist) * 0.25;
    glow *= 0.8 + sin(cycle * 1.5) * 0.2;
    
    // Add some swirling to the glow
    float swirl = fbmLoop(uv * 3.0 + vec2(sin(cycle), cos(cycle)) * 0.5, cycle);
    glow *= 0.7 + swirl * 0.5;
    
    return glow * smoothstep(0.08, 0.2, uv.y) * smoothstep(0.9, 0.7, uv.y);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    
    // Add margins to keep effect within bounds
    vec2 safeUV = uv * 0.82 + 0.09;
    
    float time = iTime;
    float cycle = time * TAU / DURATION; // Perfect cycle over duration
    
    // Get all effect components
    float fire = fireShape(safeUV, cycle, time);
    float core = fireCore(safeUV, cycle);
    float wisp = wisps(safeUV, cycle, time);
    float particle = particles(safeUV, cycle, time);
    float glow = magicalGlow(safeUV, cycle);
    
    // Color palette - mystical purple and pink
    vec3 white = vec3(1.0, 1.0, 1.0);
    vec3 hotPink = vec3(1.0, 0.45, 0.75);
    vec3 magenta = vec3(0.95, 0.25, 0.65);
    vec3 purple = vec3(0.65, 0.15, 0.85);
    vec3 deepPurple = vec3(0.4, 0.05, 0.6);
    vec3 darkPurple = vec3(0.25, 0.0, 0.4);
    
    // Fire color gradient
    vec3 fireColor = darkPurple;
    fireColor = mix(fireColor, deepPurple, smoothstep(0.0, 0.2, fire));
    fireColor = mix(fireColor, purple, smoothstep(0.15, 0.4, fire));
    fireColor = mix(fireColor, magenta, smoothstep(0.3, 0.55, fire));
    fireColor = mix(fireColor, hotPink, smoothstep(0.45, 0.7, fire));
    fireColor = mix(fireColor, white, smoothstep(0.6, 0.9, fire));
    
    // Core is always white-hot
    vec3 coreColor = mix(hotPink, white, smoothstep(0.3, 0.8, core));
    
    // Wisp color - ethereal light purple/pink
    vec3 wispColor = mix(vec3(0.7, 0.4, 0.95), vec3(1.0, 0.75, 0.95), wisp);
    
    // Particle color - bright sparkles
    vec3 particleColor = vec3(1.0, 0.9, 1.0);
    
    // Glow color - soft purple
    vec3 glowColor = vec3(0.5, 0.2, 0.7);
    
    // Combine all elements
    vec3 finalColor = vec3(0.0);
    float finalAlpha = 0.0;
    
    // Layer 1: Outer glow
    finalColor += glowColor * glow;
    finalAlpha = max(finalAlpha, glow * 0.6);
    
    // Layer 2: Main fire
    finalColor = mix(finalColor, fireColor, fire);
    finalAlpha = max(finalAlpha, fire);
    
    // Layer 3: Hot core (additive)
    finalColor += coreColor * core * 0.8;
    finalAlpha = max(finalAlpha, core);
    
    // Layer 4: Wisps
    finalColor += wispColor * wisp * 1.2;
    finalAlpha = max(finalAlpha, wisp * 0.7);
    
    // Layer 5: Particles (additive for sparkle)
    finalColor += particleColor * particle * 1.8;
    finalAlpha = max(finalAlpha, particle * 0.9);
    
    // Boost saturation and brightness
    finalColor *= 1.15;
    
    // Clamp and smooth alpha
    finalAlpha = clamp(finalAlpha, 0.0, 1.0);
    finalAlpha = smoothstep(0.01, 0.08, finalAlpha) * finalAlpha;
    
    fragColor = vec4(finalColor, finalAlpha);
}