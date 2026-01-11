// Ethereal Blue Magical Flames with Swirling Wisps
// Seamlessly looping over 1.5 seconds

#define PI 3.14159265359
#define TAU 6.28318530718
#define DURATION 1.5

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

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

// FBM with perfect looping - all offsets use sin/cos of loopTime
float fbm(vec2 p, float loopTime) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    
    for (int i = 0; i < 6; i++) {
        float phase = float(i) * 0.5;
        vec2 offset = vec2(
            sin(loopTime + phase),
            cos(loopTime + phase * 1.3)
        ) * 0.5;
        value += amplitude * noise(p * frequency + offset);
        amplitude *= 0.5;
        frequency *= 2.0;
    }
    return value;
}

// Wisp with perfect looping
float wisp(vec2 uv, float loopTime, float seed) {
    float angle = atan(uv.y, uv.x) + sin(loopTime + seed * TAU) * 0.7;
    float radius = length(uv);
    
    // All multipliers of loopTime must result in full cycles
    // sin completes a full cycle over TAU, loopTime goes 0->TAU over duration
    // So loopTime * N completes N full cycles
    float spiral = sin(angle * 4.0 + radius * 8.0 - loopTime * 2.0 + seed * TAU);
    spiral = spiral * 0.5 + 0.5;
    spiral = pow(spiral, 0.6);
    
    float fade = exp(-radius * 2.2);
    return spiral * fade;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec2 centered = (uv - 0.5) * 2.0;
    
    centered *= 1.12;
    centered.y += 0.18;
    
    // loopTime goes from 0 to TAU over DURATION seconds
    float loopTime = iTime * TAU / DURATION;
    
    float dist = length(centered);
    
    // Flame shape
    vec2 flameUV = centered;
    flameUV.x *= 1.35;
    
    float turbulence = fbm(centered * 2.5, loopTime);
    flameUV.x += (turbulence - 0.5) * 0.28 * (1.0 - centered.y * 0.35);
    
    float flameHeight = fbm(vec2(centered.x * 2.0, 0.0), loopTime) * 0.18 + 0.82;
    
    float flameDist = length(flameUV);
    float flameShape = 1.0 - smoothstep(0.0, 0.48 * flameHeight, flameDist);
    
    float taper = smoothstep(-0.6, 0.4, -centered.y);
    flameShape *= taper;
    
    // Wispy tendrils - use INTEGER multipliers for rotation
    float wisps = 0.0;
    for (int i = 0; i < 6; i++) {
        float seed = float(i) / 6.0;
        vec2 wispUV = centered;
        wispUV.y += 0.08;
        
        // Use integer rotation speeds: 1, 2, 3... to ensure full cycles
        float rotSpeed = float(i + 1);
        float rotAngle = loopTime * rotSpeed + seed * TAU;
        mat2 rot = mat2(cos(rotAngle), -sin(rotAngle), sin(rotAngle), cos(rotAngle));
        wispUV = rot * wispUV;
        
        wisps += wisp(wispUV, loopTime, seed) * (0.28 / (1.0 + float(i) * 0.3));
    }
    
    float intensity = flameShape + wisps * 0.6;
    
    // Rising particles - fract ensures perfect looping
    float particles = 0.0;
    for (int i = 0; i < 12; i++) {
        float seed = float(i) / 12.0;
        
        float risePhase = fract(iTime / DURATION + seed);
        float particleY = centered.y + 0.6 - risePhase * 1.2;
        
        // Integer multiplier for sway
        float sway = sin(loopTime * 2.0 + seed * TAU) * 0.09;
        float particleX = centered.x + sway + (hash(vec2(seed, 0.0)) - 0.5) * 0.28;
        
        vec2 particlePos = vec2(particleX, particleY);
        float particleDist = length(particlePos);
        
        float particle = exp(-particleDist * particleDist * 140.0);
        particle *= smoothstep(0.0, 0.1, risePhase) * smoothstep(1.0, 0.9, risePhase);
        
        particles += particle;
    }
    
    intensity += particles * 0.32;
    
    // Pulse uses sin which is cyclic over TAU
    float pulse = sin(loopTime) * 0.1 + 1.0;
    intensity *= pulse;
    
    // Colors
    vec3 coreColor = vec3(1.0, 1.0, 1.0);
    vec3 midColor = vec3(0.3, 0.6, 1.0);
    vec3 outerColor = vec3(0.0, 0.88, 1.0);
    
    vec3 color;
    float coreIntensity = smoothstep(0.5, 0.95, intensity);
    float midIntensity = smoothstep(0.1, 0.55, intensity);
    
    color = mix(outerColor, midColor, midIntensity);
    color = mix(color, coreColor, coreIntensity);
    
    float outerGlow = exp(-dist * 1.6) * 0.3 * pulse;
    color += outerColor * outerGlow;
    
    float shimmer = fbm(centered * 3.5, loopTime);
    color += vec3(0.06, 0.1, 0.18) * shimmer * intensity * 0.18;
    
    float alpha = smoothstep(0.0, 0.09, intensity + outerGlow * 0.45);
    alpha = clamp(alpha, 0.0, 1.0);
    
    color *= 1.08;
    
    float edgeFade = smoothstep(0.0, 0.04, uv.x) * smoothstep(1.0, 0.96, uv.x);
    edgeFade *= smoothstep(0.0, 0.04, uv.y) * smoothstep(1.0, 0.96, uv.y);
    alpha *= edgeFade;
    
    fragColor = vec4(color, alpha);
}