// Fiery Explosion Effect - One-shot, non-looping
// Intense flash -> expanding fireball -> sparks/embers -> smoke trails -> fade out

// Hash functions for randomness
float hash(float n) { return fract(sin(n) * 43758.5453123); }
float hash2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

// Smooth noise
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    
    float a = hash2(i);
    float b = hash2(i + vec2(1.0, 0.0));
    float c = hash2(i + vec2(0.0, 1.0));
    float d = hash2(i + vec2(1.0, 1.0));
    
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// FBM for complex noise patterns
float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    for(int i = 0; i < 6; i++) {
        value += amplitude * noise(p * frequency);
        amplitude *= 0.5;
        frequency *= 2.0;
    }
    return value;
}

// Turbulent noise for fire
float turbulence(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    for(int i = 0; i < 5; i++) {
        value += amplitude * abs(noise(p * frequency) * 2.0 - 1.0);
        amplitude *= 0.5;
        frequency *= 2.0;
    }
    return value;
}

// Spark/ember particle
float spark(vec2 uv, vec2 origin, vec2 velocity, float birthTime, float lifespan, float size, float t) {
    if(t < birthTime || t > birthTime + lifespan) return 0.0;
    
    float age = (t - birthTime) / lifespan;
    float fadeOut = 1.0 - smoothstep(0.5, 1.0, age);
    
    // Add gravity and drag
    vec2 pos = origin + velocity * (t - birthTime) * (1.0 - age * 0.5);
    pos.y -= 0.3 * (t - birthTime) * (t - birthTime); // gravity
    
    float dist = length(uv - pos);
    float sparkGlow = exp(-dist * dist / (size * size * (1.0 - age * 0.7)));
    
    return sparkGlow * fadeOut;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec2 center = vec2(0.5, 0.45); // slightly below center
    vec2 centered = uv - center;
    float dist = length(centered);
    float angle = atan(centered.y, centered.x);
    
    float t = iTime;
    
    // Master fade out - everything gone by t=1.0
    float masterFade = 1.0 - smoothstep(0.7, 1.0, t);
    
    // === PHASE 1: Initial Flash (t=0 to 0.15) ===
    float flashIntensity = exp(-t * 15.0) * (1.0 - smoothstep(0.0, 0.1, t) * 0.5);
    float flash = flashIntensity * exp(-dist * dist / 0.08);
    
    // === PHASE 2: Expanding Fireball Core (t=0 to 0.5) ===
    float expansion = smoothstep(0.0, 0.4, t);
    float coreRadius = 0.05 + expansion * 0.25;
    float coreFade = 1.0 - smoothstep(0.2, 0.6, t);
    
    // Turbulent fire pattern
    float fireNoise = turbulence(centered * 8.0 - vec2(0.0, t * 3.0));
    float firePattern = fbm(centered * 6.0 + vec2(fireNoise, -t * 2.0));
    
    // Core shape with noise distortion
    float distortedDist = dist + fireNoise * 0.05 - firePattern * 0.03;
    float core = 1.0 - smoothstep(coreRadius * 0.3, coreRadius, distortedDist);
    core *= coreFade;
    
    // Outer fire envelope
    float outerRadius = coreRadius * 1.8;
    float outerFire = 1.0 - smoothstep(coreRadius * 0.5, outerRadius, distortedDist);
    outerFire *= firePattern;
    outerFire *= coreFade * 0.8;
    
    // === PHASE 3: Sparks and Embers ===
    float sparksTotal = 0.0;
    float embersTotal = 0.0;
    
    // Generate many sparks flying outward
    for(int i = 0; i < 40; i++) {
        float id = float(i);
        float sparkAngle = hash(id * 1.23) * 6.28318;
        float sparkSpeed = 0.3 + hash(id * 2.34) * 0.5;
        float sparkBirth = hash(id * 3.45) * 0.15;
        float sparkLife = 0.3 + hash(id * 4.56) * 0.5;
        float sparkSize = 0.008 + hash(id * 5.67) * 0.012;
        
        vec2 vel = vec2(cos(sparkAngle), sin(sparkAngle)) * sparkSpeed;
        vel.y += 0.1; // slight upward bias
        
        sparksTotal += spark(uv, center, vel, sparkBirth, sparkLife, sparkSize, t) * (0.5 + hash(id * 6.78) * 0.5);
    }
    
    // Larger, slower embers
    for(int i = 0; i < 25; i++) {
        float id = float(i) + 100.0;
        float emberAngle = hash(id * 1.11) * 6.28318;
        float emberSpeed = 0.15 + hash(id * 2.22) * 0.25;
        float emberBirth = 0.05 + hash(id * 3.33) * 0.2;
        float emberLife = 0.4 + hash(id * 4.44) * 0.4;
        float emberSize = 0.015 + hash(id * 5.55) * 0.02;
        
        vec2 vel = vec2(cos(emberAngle), sin(emberAngle)) * emberSpeed;
        
        embersTotal += spark(uv, center, vel, emberBirth, emberLife, emberSize, t) * 0.7;
    }
    
    // === PHASE 4: Smoke Trails ===
    float smoke = 0.0;
    float smokeStart = 0.2;
    float smokeT = max(0.0, t - smokeStart);
    
    if(t > smokeStart) {
        float smokeExpand = smokeT * 0.8;
        float smokeFade = 1.0 - smoothstep(0.3, 0.8, t);
        
        // Multiple smoke layers
        for(int i = 0; i < 4; i++) {
            float layer = float(i);
            vec2 smokeOffset = vec2(
                sin(layer * 2.1 + t * 0.5) * 0.1,
                layer * 0.05 + smokeT * 0.2
            );
            
            float smokeNoise = fbm((centered - smokeOffset) * 4.0 + vec2(t * 0.5, layer));
            float smokeRing = 1.0 - smoothstep(0.1, 0.2 + smokeExpand, length(centered - smokeOffset));
            smoke += smokeRing * smokeNoise * smokeFade * 0.3;
        }
    }
    
    // === Color Mixing ===
    vec3 white = vec3(1.0, 1.0, 0.95);
    vec3 brightYellow = vec3(1.0, 0.95, 0.4);
    vec3 orange = vec3(1.0, 0.5, 0.1);
    vec3 red = vec3(0.9, 0.2, 0.05);
    vec3 darkRed = vec3(0.4, 0.1, 0.02);
    vec3 smokeColor = vec3(0.15, 0.12, 0.1);
    
    // Flash color (white-yellow)
    vec3 flashCol = mix(white, brightYellow, 0.3) * flash * 3.0;
    
    // Core fireball gradient (center hot white -> orange -> red edge)
    float coreHeat = core * (1.0 - distortedDist / coreRadius);
    vec3 coreCol = mix(darkRed, red, coreHeat);
    coreCol = mix(coreCol, orange, coreHeat * coreHeat);
    coreCol = mix(coreCol, brightYellow, pow(coreHeat, 3.0));
    coreCol = mix(coreCol, white, pow(coreHeat, 5.0));
    coreCol *= core * 2.0;
    
    // Outer fire
    vec3 outerCol = mix(darkRed, orange, outerFire) * outerFire * 1.5;
    
    // Sparks (bright yellow-white)
    vec3 sparkCol = mix(orange, brightYellow, 0.7) * sparksTotal * 2.0;
    
    // Embers (orange-red)
    vec3 emberCol = mix(red, orange, 0.5) * embersTotal * 1.5;
    
    // Smoke
    vec3 smokeCol = smokeColor * smoke;
    
    // Combine all layers
    vec3 finalColor = vec3(0.0);
    float finalAlpha = 0.0;
    
    // Add smoke first (background)
    finalColor += smokeCol;
    finalAlpha = max(finalAlpha, smoke * 0.6);
    
    // Add outer fire
    finalColor += outerCol;
    finalAlpha = max(finalAlpha, outerFire * 0.9);
    
    // Add core
    finalColor += coreCol;
    finalAlpha = max(finalAlpha, core);
    
    // Add flash (additive)
    finalColor += flashCol;
    finalAlpha = max(finalAlpha, flash);
    
    // Add embers
    finalColor += emberCol;
    finalAlpha = max(finalAlpha, embersTotal * 0.8);
    
    // Add sparks (brightest, on top)
    finalColor += sparkCol;
    finalAlpha = max(finalAlpha, sparksTotal);
    
    // Apply master fade
    finalColor *= masterFade;
    finalAlpha *= masterFade;
    
    // Clamp and output
    finalColor = clamp(finalColor, 0.0, 1.0);
    finalAlpha = clamp(finalAlpha, 0.0, 1.0);
    
    fragColor = vec4(finalColor, finalAlpha);
}